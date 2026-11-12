# Backend changes – November 2026 (stages 0–6, 9, 10)

**Scope:** backend only (`Application/V3/backend/odoo_client.py`, `main.py`, new `audit.py`, the launcher, settings, tests).
**Not touched:** the AI prompt, tool definitions, model choice, the chat screen. Two small edits in `agent.py` (approval expiry + audit lines) are the only exceptions.
**Tested:** 40 automated tests, all passing, against Odoo 20 Community with the seed data, on Python 3.11 and 3.13. The AI in the tests is a scripted stand-in (`tests/fake_ollama.py`), not llama3.1.

## What changed, and the evidence

| Stage | Change | Before → after (measured) |
|---|---|---|
| 0 | Pinned Python versions; `requirements-dev.txt`; `.env.example` without the fake Teams URL; `.gitignore`; removed committed `__pycache__` | The template's placeholder webhook made the app try to post after every create → now empty and ignored |
| 1 | One Odoo connection **per thread**, timeouts (`ODOO_TIMEOUT`), one retry for reads only | 40 parallel requests: **28 failed → 0 failed** |
| 2 | Odoo errors become **one short line** (no traceback, no server paths) | `Invalid field '['` error was a 2 KB traceback → `ValueError: Invalid field '[' on 'res.partner'` |
| 3 | **Read allow-list**: only `res.partner`, `product.product`, `sale.order`, `account.move` (customer invoices/credit notes only), named fields; unknown fields are left out; **row limit** (`ODOO_READ_LIMIT`, default 50); lists sent as text are understood | AI could read `res.users`, `ir.config_parameter` → refused and logged. Floyd's real failure ("fields as text") **now works without changing the AI** |
| 4 | **Create allow-list**: only draft quotations and draft customer invoices; only known fields (others are dropped and reported); `move_type` forced to `out_invoice`; quantity must be > 0; customer and product must be real Odoo ids; only new lines; **prices from Odoo** (`ODOO_ALLOW_AI_PRICES=false`) | Invoice at AI price 10.00 → **Odoo price 50.00**; AI's `"state": "sale"` → ignored, record stays draft |
| 5 | Approvals **expire** (`APPROVAL_TIMEOUT_SECONDS`, default 300); a closed browser releases its approval immediately | 45 abandoned approvals: **server froze → next chat answers in 0.02 s** |
| 6 | CORS only for the chat UI; the launcher no longer opens the UI to the network (`UI_ON_NETWORK=1` to opt in) and works on Windows/macOS/Linux; `/api/health` really asks Odoo | `Network: http://192.168.…` exposure gone by default |
| 9 | **Audit log** `Application/V3/logs/audit.jsonl` (git-ignored, append-only): `approval_requested`, `approval_answered`, `approval_expired`, `created`, `create_blocked`, `create_failed`, `read_blocked` | There was no record of who approved what |
| 10 | **Tests**: `Application/V3/tests/` (offline safety rules + Odoo integration + end-to-end API) | No tests → 40 tests |

## Settings (all optional, in `Application/V3/.env`)
| Setting | Default | Meaning |
|---|---|---|
| `ODOO_TIMEOUT` | 30 | Seconds to wait for Odoo |
| `ODOO_READ_LIMIT` | 50 | Max records per AI read |
| `ODOO_ALLOW_AI_PRICES` | false | `true` = keep a price the AI sends |
| `APPROVAL_TIMEOUT_SECONDS` | 300 | Wait for approve/decline |
| `AUDIT_LOG_PATH` | logs/audit.jsonl | Relative to `Application/V3` |
| `CORS_ORIGINS` | http://localhost:5173,http://127.0.0.1:5173 | Browser origins allowed |
| `UI_ON_NETWORK` | (unset) | `1` = launcher opens the UI to the network |

## How to run the tests (Windows, Command Prompt, from the repo root)
```
.venv\Scripts\python.exe -m pip install -r Application\V3\requirements-dev.txt
.venv\Scripts\python.exe -m pytest Application\V3\tests -v
```
Odoo must be running with the seed data; the tests use `Application\V3\.env`. They **create a few draft quotations/invoices** (marked `pytest`). Without Odoo, the Odoo tests are skipped and the 21 offline tests still run.

## For Marija (AI & chat) – what the AI now receives
- Tool errors keep the same shape `{"error": "..."}`, but the message is short and readable.
- A successful create now returns `{"status": "success", "created_id": 12, "state": "draft"}` plus, when something was dropped, `"ignored_fields": [...]` and `"note": "Prices were taken from Odoo, not from the request."`.
- New approval result: `{"status": "expired", "message": "No approval was given in time. Nothing was created."}`.
- Refused reads: `{"error": "Reading 'res.users' is not allowed. Allowed: ..."}`.
- Still on the AI side (unchanged): after a failed tool call the second AI call can still make things up; lost line breaks in the chat; the hard-coded model name.

## Not done yet (needs the team)
- **Stage 7 – name matching** (exact match first, "did you mean …?"): needs the data-contract decision D3 and a way for the chat to show the question.
- **Stage 8 – duplicate check**: needs a decision on block vs. warn and a warning in the approval screen.
- **Revoke the leaked secrets** (Odoo password and Teams webhook in V1/V2): a manual task, not code.
- Name lookups still pick the first partial match (stage 7).

## Risk to know about
The limited `ai_agent` user is **allowed by Odoo to confirm sales orders and post invoices** (tested). The AI cannot do this today only because the backend's create allow-list has no such action. Do not add confirm/post actions until approvals, the audit log and the duplicate check are complete – a posted invoice gets a legal number and cannot simply be deleted.
