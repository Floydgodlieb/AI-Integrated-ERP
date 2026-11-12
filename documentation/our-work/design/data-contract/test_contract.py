"""Run: python test_contract.py   (needs: pip install pydantic)
Checks that every example in contract_examples.json is valid against the draft schema,
and that a few BAD outputs are rejected."""
import json, pathlib, sys
from pydantic import ValidationError
sys.path.insert(0, str(pathlib.Path(__file__).parent))
from schemas_draft import AIEnvelope

here = pathlib.Path(__file__).parent
ok = bad = 0
for ex in json.loads((here / "contract_examples.json").read_text(encoding="utf-8")):
    try:
        AIEnvelope.model_validate(ex["ai_output"]); ok += 1; print("valid   ", ex["id"])
    except ValidationError as e:
        bad += 1; print("INVALID ", ex["id"], str(e)[:200])

must_fail = {
  "AI sends an Odoo id": {"result": {"action": "create_invoice", "customer_name": "Pepsi", "partner_id": 6, "lines": [{"product_name": "Chair", "quantity": 1}]}},
  "negative quantity":   {"result": {"action": "create_invoice", "customer_name": "Pepsi", "lines": [{"product_name": "Chair", "quantity": -2}]}},
  "empty lines":         {"result": {"action": "create_invoice", "customer_name": "Pepsi", "lines": []}},
  "unknown action":      {"result": {"action": "delete_everything"}},
  "free odoo model":     {"result": {"action": "lookup", "what": "ir.config_parameter"}},
  "bad date":            {"result": {"action": "create_invoice", "customer_name": "Pepsi", "lines": [{"product_name": "Chair", "quantity": 1}], "invoice_date": "tomorrow"}},
}
for name, payload in must_fail.items():
    try:
        AIEnvelope.model_validate(payload); print("NOT REJECTED (bug):", name); bad += 1
    except ValidationError:
        print("rejected", name)

schema = AIEnvelope.model_json_schema()
print("JSON schema generated for Ollama 'format': keys =", sorted(schema.keys()), "| size", len(json.dumps(schema)), "bytes")
print("RESULT:", "ALL GOOD" if bad == 0 else f"{bad} problem(s)")
sys.exit(1 if bad else 0)
