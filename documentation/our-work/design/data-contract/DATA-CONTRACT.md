# Data contract: what the AI passes to the backend

**For:** Floyd (backend) and Marija (AI & chat). **Goal:** agree on this *before* building, so the AI side and the backend side fit together on the first try.
**Status:** DRAFT v0.1 – nothing here is final until both of you tick the boxes in §3 and merge `schemas.py`.

## 1. Why this matters (in 5 lines)
Today the AI sends free-form data to the backend: any Odoo model, any field, names or IDs, prices it invents (`Application/V3.1/backend/agent.py`). That caused the problems in the handover report (wrong matches, trusted prices, read-anything). A **contract** fixes it: the AI may only produce a small, strict JSON shape; the backend checks it, and the backend – not the AI – talks to Odoo.

```
User text ─► AI (Marija) ─► JSON that follows the contract ─► Backend (Floyd): validate, look up in Odoo, price, duplicates
                                                         ◄─ reply: needs_approval / needs_clarification / rejected / created
```

## 2. The draft contract in one page
Files: `schemas_draft.py` (the schema, runs with Pydantic), `contract_examples.json` (9 examples), `test_contract.py` (checks examples and that bad outputs are rejected; **passes today**).

**Rules (proposal):**
1. The AI **never** sends Odoo IDs, Odoo model names, Odoo field names (`partner_id`, `move_type`…) or taxes. It sends what the **user said**: `customer_name`, `product_name`, `quantity`.
2. The AI picks **exactly one action** from a closed list: `create_invoice`, `create_sales_order`, `lookup`, `ask_clarification`, `refuse`.
3. If the user didn't say something, the AI leaves it `null` or asks (`ask_clarification`). **It must not guess.**
4. The AI never decides money. `unit_price` is only filled if the user explicitly stated a price; otherwise the backend uses Odoo's price. A given price triggers a `PRICE_OVERRIDE` warning at approval.
5. Unknown keys are an error (`extra="forbid"`), and every message carries `schema_version`.

**AI → backend (example):**
```json
{"schema_version": "0.1",
 "result": {"action": "create_invoice", "customer_name": "Pepsi",
            "lines": [{"product_name": "Chair", "quantity": 3, "unit_price": null}],
            "invoice_date": null, "from_order": null, "source_text": "Invoice Pepsi for 3 chairs"}}
```
**Backend → UI/AI** has four shapes (see `schemas_draft.py`):

| status | When | Carries |
|---|---|---|
| `needs_clarification` | customer/product ambiguous, not found, or missing | `field`, `reason` (AMBIGUOUS / NOT_FOUND / MISSING), `candidates`, `question` |
| `needs_approval` | everything resolved | `action_id` (pending, expires), resolved customer + lines, **totals from Odoo**, `warnings` |
| `rejected` | validation/permission/duplicate/expired/Odoo error | `code`, `message` |
| `created` | after approval | Odoo model + id, `state: "draft"` |

## 3. Decisions to agree on (tick when both agree)
Each has my **recommended default** – change it if you have a better reason.

| # | Decision | Recommended default | Who mainly decides | Agreed |
|---|---|---|---|---|
| D1 | AI sends **names**, backend resolves to IDs (not the AI) | Yes | Floyd | ☐ |
| D2 | Closed action list for v1 | `create_invoice`, `create_sales_order`, `lookup`, `ask_clarification`, `refuse` (no update/delete) | both | ☐ |
| D3 | Name matching: **exact match wins**, otherwise partial; >1 partial candidate → `AMBIGUOUS` | Yes ("Pepsi" → Pepsi; "Jansen" → ask) | Floyd | ☐ |
| D4 | Price: **Odoo price list by default**; AI price only as explicit user override + warning | Yes | Floyd | ☐ |
| D5 | Who creates a **new customer**? | Nobody via AI in v1: `NOT_FOUND` → user creates it in Odoo (the limited `ai_agent` user *cannot* create customers) | both + Tijn | ☐ |
| D6 | Dates: ISO `YYYY-MM-DD`, `null` = today; the AI must not convert "next Friday" itself (backend/UI does, or AI asks) | ISO only | Marija | ☐ |
| D7 | Quantities: positive numbers; decimals allowed? | `> 0`, decimals allowed | Floyd | ☐ |
| D8 | `lookup` is a **named query** (`customers`, `products`, `sales_orders`, `invoices`) + search text, never a free Odoo model/domain | Yes | Floyd | ☐ |
| D9 | Language of user input | English first; Dutch later (product names stay as written) | Marija + Tijn | ☐ |
| D10 | Where the schema lives + who may change it | `Application/V3.1/backend/schemas.py`; changes via PR, **both** review, bump `schema_version` | both | ☐ |
| D11 | Confidence scores from the AI | **No** in v1 (small models' self-reported confidence isn't reliable); use validation + clarification instead | Marija | ☐ |
| D12 | Error codes & warnings list (§2 table + `Warning_` codes) | Keep list small; add only with a test | Floyd | ☐ |

## 4. 45-minute agreement meeting (Floyd + Marija; Tijn/Anastasia may listen)
1. (5 min) Read §1–2 together; run `python test_contract.py` (it passes).
2. (25 min) Go through D1–D12; tick or change each. Write changes directly into `schemas_draft.py` and add one example to `contract_examples.json` per changed rule.
3. (10 min) Walk through the 9 examples out loud: "AI says X → backend does Y → user sees Z". Fix anything unclear.
4. (5 min) Agree the **first experiment** (below) and who does what.

## 5. Things neither of us could verify yet (do these right after the meeting)
- **Marija:** Can Llama 3.1 fill this schema through Ollama's `format=` structured output? The union of 5 actions produces a `oneOf` schema; Ollama may handle it badly. *Fallback:* a flatter schema (one object with an `action` enum and optional fields). Test with the 9 examples' `user_says` texts and record accuracy → first experiment-log entry. *(I could not run a real model.)*
- **Floyd:** Does exact-first matching (D3) behave on the seeded test data (`Pepsi` vs `Pepsi Cola Bottling`, `Jansen Bouw` vs `Jansen & Zonen`, `Chair` vs `Chair Floor Protection`)? Write 5 unit tests from the examples.
- **Both:** What should the user see for `needs_approval` (the approval card)? Marija draws it, Floyd confirms every field exists in the backend reply.
- **Anastasia:** converts `contract_examples.json` into the first rows of the 50-prompt test set (`user_says`, expected action, expected outcome).

## 6. How this plugs into the existing code
| Today (`Application/V3.1/backend/`) | After the contract |
|---|---|
| `agent.py` `odoo_create(model, values)` – free object | one tool/format that must validate as `AIEnvelope` |
| `agent.py` `resolve_entities()` `ilike` first hit | resolver with D3 rules, returns candidates |
| `odoo_client.py` `_apply_auto_corrections()` | removed – the AI no longer sends Odoo field names |
| `odoo_search_read(model, domain, fields)` | `lookup` (named queries, allow-listed fields) |
| approval = blocking thread | `needs_approval` with `action_id` + expiry (Floyd's task) |
