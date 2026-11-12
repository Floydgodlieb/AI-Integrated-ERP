# Backend changes – November 2026 (stages 0–6, 9, 10)

> **Where the code is:** these changes are **V3.1** in `Application/V3.1/`. `Application/V3/` is the previous group's original V3, kept **unchanged** for comparison (before/after measurements). Do new work in V3.1.

**Scope:** backend only (`Application/V3.1/backend/odoo_client.py`, `main.py`, new `audit.py`, the launcher, settings, tests).
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
| 1b | **`localhost` → `127.0.0.1`** for the Odoo connection (automatic, also for existing `.env` files); new default everywhere | Measured on Floyd's Windows PC: **2.08 s → 0.03 s per new Odoo connection**. The abandoned-approvals test took 204 s on Windows before this fix |
| 9 | **Audit log** `Application/V3.1/logs/audit.jsonl` (git-ignored, append-only): `approval_requested`, `approval_answered`, `approval_expired`, `created`, `create_blocked`, `create_failed`, `read_blocked` | There was no record of who approved what |
| 10 | **Tests**: `Application/V3.1/tests/` (offline safety rules + Odoo integration + end-to-end API) | No tests → 40 tests |

## Settings (all optional, in `Application/V3.1/.env`)
| Setting | Default | Meaning |
|---|---|---|
| `ODOO_TIMEOUT` | 30 | Seconds to wait for Odoo |
| `ODOO_READ_LIMIT` | 50 | Max records per AI read |
| `ODOO_ALLOW_AI_PRICES` | false | `true` = keep a price the AI sends |
| `APPROVAL_TIMEOUT_SECONDS` | 300 | Wait for approve/decline |
| `AUDIT_LOG_PATH` | logs/audit.jsonl | Relative to `Application/V3.1` |
| `CORS_ORIGINS` | http://localhost:5173,http://127.0.0.1:5173 | Browser origins allowed |
| `UI_ON_NETWORK` | (unset) | `1` = launcher opens the UI to the network |

## How to run the tests (Windows, Command Prompt, from the repo root)
```
.venv\Scripts\python.exe -m pip install -r Application\V3.1\requirements-dev.txt
.venv\Scripts\python.exe -m pytest Application\V3.1\tests -v
```
To save the run as evidence, use `.venv\Scripts\python.exe Setup\run_tests.py --who yourname` instead (see [TEST-RESULTS.md](../tests/TEST-RESULTS.md)).

Odoo must be running with the seed data; the tests use `Application\V3.1\.env`. They **create a few draft quotations/invoices** (marked `pytest`). Without Odoo, the Odoo tests are skipped and the 21 offline tests still run.

## For Marija (AI & chat) – what the AI now receives
- Tool errors keep the same shape `{"error": "..."}`, but the message is short and readable.
- A successful create now returns `{"status": "success", "created_id": 12, "state": "draft"}` plus, when something was dropped, `"ignored_fields": [...]` and `"note": "Prices were taken from Odoo, not from the request."`.
- New approval result: `{"status": "expired", "message": "No approval was given in time. Nothing was created."}`.
- Refused reads: `{"error": "Reading 'res.users' is not allowed. Allowed: ..."}`.
- The chat UI's dev proxy (`chat-UI/vite.config.js`) still points at `http://localhost:8001`. Node usually copes with that, but if the chat feels slow on Windows, try `http://127.0.0.1:8001` there (your file, so not changed here).
- Still on the AI side (unchanged): after a failed tool call the second AI call can still make things up; lost line breaks in the chat; the hard-coded model name.

### Task for Marija: the approval box hides what you approve (found in the first real test, 12 Nov 2026)
**Problem.** With the real llama3.1, the approval box showed only *"Create Invoice | Customer: Pepsi | 1 in…"*. The text is cut off, and even the full text does not say which product, how many, or at what price. A human cannot check what they approve, which defeats the point of the approval step.

**Cause 1 – display** (`Application/V3.1/chat-UI/src/Chat.css`): `.confirm-detail` has `white-space: nowrap; overflow: hidden; text-overflow: ellipsis;` inside `.confirm-dialog` with `max-width: 400px`.
Suggested fix: remove those three lines (or use `white-space: pre-wrap`) and widen the dialog (e.g. `max-width: 560px`).

**Cause 2 – content** (`Application/V3.1/backend/agent.py`, `_summarize_create`): it only counts lines ("1 invoice line(s)").
Suggested fix: list each line as *product × quantity @ price*, with the price taken from Odoo (`product.product` `list_price`, "excl. tax"), and warn when the AI tried to set its own price. This matches `needs_approval` in the data-contract draft (lines, totals, warnings). Agree the exact layout with Floyd.

**Related, seen in the same test:**
- Created records show a grey **"Executed"** bubble; a short "Created draft quotation S00003" would be clearer.
- The AI wrote *"Order Name: (Untitled)"*: the create result only contains the id, so the AI invented a name. (Backend option for Floyd: return Odoo's real name, e.g. `S00003`, in the create result.)

## Not done yet (needs the team)
- **Stage 7 – name matching** (exact match first, "did you mean …?"): needs the data-contract decision D3 and a way for the chat to show the question.
- **Stage 8 – duplicate check**: needs a decision on block vs. warn and a warning in the approval screen.
- **Revoke the leaked secrets** (Odoo password and Teams webhook in V1/V2): a manual task, not code.
- Name lookups still pick the first partial match (stage 7).

## Risk to know about
The limited `ai_agent` user is **allowed by Odoo to confirm sales orders and post invoices** (tested). The AI cannot do this today only because the backend's create allow-list has no such action. Do not add confirm/post actions until approvals, the audit log and the duplicate check are complete – a posted invoice gets a legal number and cannot simply be deleted.
