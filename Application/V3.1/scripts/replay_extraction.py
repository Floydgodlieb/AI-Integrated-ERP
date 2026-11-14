"""Replay the draft AI-to-backend examples against Ollama and score extraction."""

import argparse
import json
import os
import platform
import statistics
import sys
import time
from datetime import date, datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

APP_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(APP_DIR))

from backend.intent_schema import ACTION_NAMES, AI_INTENT_SCHEMA  # noqa: E402

PROMPT = """Extract one action from the user's request as JSON matching the supplied schema.
Copy customer and product names from the request. Do not guess missing details.
Use ask_clarification when a required detail is missing. Use refuse for unsupported actions.
Never extract or set a price. Odoo supplies prices and taxes. If the user asks for a different price, ask whether to use Odoo's price.
Include an ISO date only when stated.
For lookups, use a limit of 10 unless the user asks for another limit, up to 50.
Return only the fields needed for the selected action.
For a read request, use one named lookup. Never return ERP facts or Odoo IDs."""


def compare_expected(expected, actual, parent_action=None):
    """Check expected fields and reject non-empty fields the prompt did not supply."""
    if isinstance(expected, dict):
        if not isinstance(actual, dict):
            return False
        action = expected.get("action", parent_action)
        if not all(key in actual and compare_expected(value, actual[key], action)
                   for key, value in expected.items()):
            return False
        neutral = {
            "customer_name": None,
            "lines": [],
            "invoice_date": None,
            "what": None,
            "search_text": None,
            "missing": [],
            "question": None,
            "reason": None,
        }
        for key, value in actual.items():
            if key in expected:
                continue
            if key == "question" and action == "ask_clarification" and isinstance(value, str) and value.strip():
                continue
            if key == "reason" and action == "refuse" and isinstance(value, str) and value.strip():
                continue
            if key in neutral and value == neutral[key]:
                continue
            return False
        return True
    if isinstance(expected, list):
        return isinstance(actual, list) and len(expected) == len(actual) and all(
            compare_expected(expected_value, actual_value, parent_action)
            for expected_value, actual_value in zip(expected, actual)
        )
    return expected == actual


def valid_output(value):
    if not isinstance(value, dict) or value.get("schema_version") != "0.1":
        return False
    result = value.get("result")
    if not isinstance(result, dict) or result.get("action") not in ACTION_NAMES:
        return False
    if result["action"] in {"create_invoice", "create_sales_order"}:
        customer = result.get("customer_name")
        lines = result.get("lines")
        if not isinstance(customer, str) or not customer.strip() or not isinstance(lines, list) or not lines:
            return False
        for line in lines:
            if not isinstance(line, dict) or not isinstance(line.get("product_name"), str) or not line["product_name"].strip():
                return False
            quantity = line.get("quantity")
            if isinstance(quantity, bool) or not isinstance(quantity, (int, float)) or quantity <= 0:
                return False
        invoice_date = result.get("invoice_date")
        if invoice_date is not None:
            if not isinstance(invoice_date, str):
                return False
            try:
                date.fromisoformat(invoice_date)
            except ValueError:
                return False
    if result["action"] == "lookup" and result.get("what") not in {"customers", "products", "sales_orders", "invoices"}:
        return False
    if result["action"] == "ask_clarification" and not result.get("question"):
        return False
    if result["action"] == "refuse" and not result.get("reason"):
        return False
    return True


def ollama_url():
    host = os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434").rstrip("/")
    if not host.startswith(("http://", "https://")):
        host = f"http://{host}"
    return f"{host}/api/chat"


def ask_ollama(url, model, user_says, timeout):
    body = {
        "model": model,
        "messages": [
            {"role": "system", "content": PROMPT},
            {"role": "user", "content": user_says},
        ],
        "format": AI_INTENT_SCHEMA,
        "stream": False,
        "options": {"temperature": 0},
    }
    keep_alive = os.getenv("OLLAMA_KEEP_ALIVE", "").strip()
    if keep_alive:
        body["keep_alive"] = keep_alive

    request = Request(url, data=json.dumps(body).encode("utf-8"), headers={"Content-Type": "application/json"})
    started = time.perf_counter()
    with urlopen(request, timeout=timeout) as response:
        payload = json.loads(response.read().decode("utf-8"))
    request_ms = (time.perf_counter() - started) * 1000
    return payload, request_ms


def build_summary(model, url, rows, prompt_count, status):
    request_times = [row["request_ms"] for row in rows if row.get("request_ms") is not None]
    return {
        "model": model,
        "ollama_url": url,
        "schema_version": "0.1",
        "status": status,
        "recorded_at_utc": datetime.now(timezone.utc).isoformat(),
        "environment": {
            "platform": platform.platform(),
            "machine": platform.machine(),
            "processor": platform.processor(),
            "python": platform.python_version(),
        },
        "counts": {
            "prompts": prompt_count,
            "attempted": len(rows),
            "completed": len(request_times),
            "valid_schema": sum(row["valid_schema"] for row in rows),
            "correct_action": sum(row["action_correct"] for row in rows),
            "correct_expected_fields": sum(row["expected_fields_correct"] for row in rows),
        },
        "latency_ms": {
            "first_request": request_times[0] if request_times else None,
            "median_after_first": round(statistics.median(request_times[1:]), 1) if len(request_times) > 1 else None,
            "all_requests_median": round(statistics.median(request_times), 1) if request_times else None,
        },
        "results": rows,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", default=os.getenv("OLLAMA_MODEL", "llama3.1"))
    parser.add_argument("--examples", type=Path, default=APP_DIR / "benchmarks" / "extraction-prompts.json")
    parser.add_argument("--output", type=Path, default=None, help="JSON results path; defaults to a dated file in results/.")
    parser.add_argument("--timeout", type=float, default=180)
    parser.add_argument("--limit", type=int, default=None, help="Run only the first N prompts for a short pilot.")
    args = parser.parse_args()

    examples = json.loads(args.examples.read_text(encoding="utf-8"))
    if args.limit is not None:
        examples = examples[:max(0, args.limit)]
    if not examples:
        parser.error("No prompts selected.")
    url = ollama_url()
    output = args.output or (APP_DIR / "results" / f"structured-extraction-{datetime.now().strftime('%Y%m%d-%H%M%S')}.json")
    rows = []
    for index, example in enumerate(examples, start=1):
        try:
            response, request_ms = ask_ollama(url, args.model, example["user_says"], args.timeout)
        except (HTTPError, URLError, TimeoutError, OSError) as error:
            print(f"Could not reach Ollama at {url}: {error}", file=sys.stderr)
            rows.append({
                "id": example["id"],
                "user_says": example["user_says"],
                "valid_schema": False,
                "action_correct": False,
                "expected_fields_correct": False,
                "request_ms": None,
                "ollama_total_ms": None,
                "output": None,
                "error": f"{type(error).__name__}: {error}",
            })
            summary = build_summary(args.model, url, rows, len(examples), "partial")
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
            print(f"Saved partial results: {output}", file=sys.stderr)
            return 2

        raw = response.get("message", {}).get("content", "")
        try:
            parsed = json.loads(raw)
            is_valid = valid_output(parsed)
            result = parsed.get("result") if isinstance(parsed, dict) else None
        except (TypeError, json.JSONDecodeError):
            parsed = None
            is_valid = False
            result = None

        expected = example["expected"]
        action_ok = bool(result and result.get("action") == expected.get("action"))
        fields_ok = bool(result and compare_expected(expected, result))
        rows.append({
            "id": example["id"],
            "user_says": example["user_says"],
            "valid_schema": is_valid,
            "action_correct": action_ok,
            "expected_fields_correct": fields_ok,
            "request_ms": round(request_ms, 1),
            "ollama_total_ms": round(response.get("total_duration", 0) / 1_000_000, 1),
            "output": parsed,
        })
        state = "valid" if is_valid else "invalid"
        print(f"{index}/{len(examples)} {example['id']}: {state}, {request_ms:.0f} ms")

    summary = build_summary(args.model, url, rows, len(examples), "complete")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(
        f"Score: schema {summary['counts']['valid_schema']}/{len(rows)}, "
        f"action {summary['counts']['correct_action']}/{len(rows)}, "
        f"fields {summary['counts']['correct_expected_fields']}/{len(rows)}"
    )
    print(f"First request: {summary['latency_ms']['first_request']} ms; "
          f"median after first: {summary['latency_ms']['median_after_first']} ms")
    print(f"Saved: {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
