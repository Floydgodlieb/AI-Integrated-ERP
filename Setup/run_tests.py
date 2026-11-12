#!/usr/bin/env python3
"""
run_tests.py - run the V3.1 backend tests and save the full report as test evidence.

Run it with the Python of the project's virtual environment, from the repo folder:
  Windows:      .venv\\Scripts\\python.exe Setup\\run_tests.py --who floyd
  macOS/Linux:  .venv/bin/python Setup/run_tests.py --who floyd

It writes   documentation/our-work/tests/runs/<date>_<time>_<who>.txt
with a header (date, who, operating system, Python, Odoo version, Git commit) followed by
the complete pytest output, and prints a table row you can paste into
documentation/our-work/tests/TEST-RESULTS.md.

Needs: Odoo running with the seed data and Application/V3.1/.env (same as the tests).
Note: the tests create a few DRAFT quotations and invoices in that database.
"""
import argparse
import os
import platform
import re
import subprocess
import sys
import xmlrpc.client
from datetime import datetime
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
TESTS = REPO / "Application" / "V3.1" / "tests"
RUNS = REPO / "documentation" / "our-work" / "tests" / "runs"
ENV_FILE = REPO / "Application" / "V3.1" / ".env"


def odoo_version() -> str:
    url = "http://127.0.0.1:8069"
    if ENV_FILE.exists():
        for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
            if line.strip().startswith("ODOO_URL="):
                url = line.split("=", 1)[1].split("#")[0].strip() or url
    url = url.replace("://localhost", "://127.0.0.1", 1)
    try:
        return xmlrpc.client.ServerProxy(f"{url}/xmlrpc/2/common").version()["server_version"]
    except Exception:
        return "not reachable"


def git(*args) -> str:
    try:
        return subprocess.run(["git", *args], cwd=REPO, capture_output=True, text=True, timeout=10).stdout.strip()
    except Exception:
        return "?"


def main():
    ap = argparse.ArgumentParser(description="Run the V3.1 tests and save the report.")
    ap.add_argument("--who", required=True, help="your first name, e.g. floyd (used in the file name)")
    a = ap.parse_args()
    who = re.sub(r"[^a-z0-9-]", "", a.who.lower()) or "unknown"

    now = datetime.now()
    header = {
        "Date": now.strftime("%Y-%m-%d %H:%M"),
        "Who": who,
        "OS": platform.platform(),
        "Python": platform.python_version(),
        "Odoo": odoo_version(),
        "Git": f"{git('rev-parse', '--abbrev-ref', 'HEAD')} @ {git('rev-parse', '--short', 'HEAD')}",
    }
    print("Running tests ...  (" + ", ".join(f"{k}: {v}" for k, v in header.items()) + ")")

    result = subprocess.run(
        [sys.executable, "-m", "pytest", str(TESTS), "-v", "-rA", "--durations=5", "-p", "no:cacheprovider"],
        cwd=REPO, capture_output=True, text=True, env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"})
    output = result.stdout + result.stderr

    RUNS.mkdir(parents=True, exist_ok=True)
    report = RUNS / f"{now.strftime('%Y-%m-%d_%H%M')}_{who}.txt"
    head = "\n".join(f"{k:7}: {v}" for k, v in header.items())
    report.write_text(f"{head}\nCommand: pytest Application/V3.1/tests -v -rA --durations=5\n{'=' * 70}\n{output}",
                      encoding="utf-8")

    summary = next((l.strip("= ").strip() for l in reversed(output.splitlines())
                    if re.search(r"\b(passed|failed|error|skipped|no tests ran)\b", l)), "no summary found")
    status = "✅" if result.returncode == 0 else "❌"
    rel = report.relative_to(REPO / "documentation" / "our-work" / "tests").as_posix()
    print(f"\n{status} {summary}")
    print(f"Report saved: {report.relative_to(REPO).as_posix()}")
    print("\nPaste this row into documentation/our-work/tests/TEST-RESULTS.md (table 'Automated test runs'):")
    print(f"| {header['Date']} | {who} | {platform.system()} | {header['Python']} | {header['Odoo']} | "
          f"`{git('rev-parse', '--short', 'HEAD')}` | {status} {summary} | [report]({rel}) |")
    sys.exit(result.returncode)


if __name__ == "__main__":
    main()
