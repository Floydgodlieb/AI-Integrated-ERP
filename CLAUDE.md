# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is
A chat assistant for **Odoo 20 Community**: a local LLM (Ollama, default `llama3.1`) turns a user's sentence into one structured action; the backend resolves names to Odoo records, shows an approval card, and creates a **draft** quotation or customer invoice in Odoo over XML-RPC. University project taken over from a previous group.

## Versions – work only in `Application/V3.1`
| Folder | Status |
|---|---|
| `Application/V1`, `V2` | Previous group's prototypes. Contain a leaked Odoo password and Teams webhook – never reuse, never copy from |
| `Application/V3` | Previous group's final version, kept **byte-for-byte unchanged** for before/after comparisons – do not edit |
| `Application/V3.1` | **Current version** (FastAPI backend + React/Vite chat UI) |
| `V4` | Reserved for the planned redesign (data contract in `documentation/our-work/design/data-contract/`) |

## Commands
The team uses Windows Command Prompt; paths below are from the repo root (use `\` on Windows).

```bash
# one-time: Python env + packages (Python 3.11+)
python -m venv .venv
.venv/bin/python -m pip install -r Application/V3.1/requirements-dev.txt   # backend + pytest
(cd Application/V3.1/chat-UI && npm install)

# Odoo test data + limited ai_agent user (idempotent; --check = dry run)
python Setup/seed_odoo.py --db odoo --user <admin-email> --password <pw> --create-agent-user --agent-password <pw>
python Setup/check_setup.py --env-file Application/V3.1/.env               # read-only health check of the whole chain

# run the app (backend :8001 + UI :5173); needs Application/V3.1/.env (copy .env.example)
cd Application/V3.1 && ../../.venv/bin/python main.py                       # UI_ON_NETWORK=1 to expose to LAN

# tests (Odoo-dependent ones skip if Odoo is down; they create draft records in that DB)
.venv/bin/python -m pytest Application/V3.1/tests -v
.venv/bin/python -m pytest Application/V3.1/tests/test_api.py::test_pick_from_the_list_without_retyping -v
.venv/bin/python Setup/run_tests.py --who <name>   # runs all tests, saves report to documentation/our-work/tests/runs/

# chat UI
(cd Application/V3.1/chat-UI && npm run lint && npm run build)

# real-model extraction benchmark (needs Ollama)
cd Application/V3.1 && ../../.venv/bin/python scripts/replay_extraction.py --model llama3.1
```
Tests read Odoo credentials from `Application/V3.1/.env` or `TEST_ODOO_URL/DB/USER/PASS`. Python deps are pinned exactly in `backend/requirements.txt`.

## Architecture (request flow)
1. **`chat-UI/src/Chat.jsx`** posts to `/api/chat` and reads a Server-Sent Events stream (`status`, `tool_call`, `confirmation_required`, `token`, `metrics`, `done`); the approval card answers via `/api/confirm/{conv_id}`.
2. **`backend/main.py`** runs the blocking agent generator in worker threads (`anyio.to_thread.run_sync(..., abandon_on_cancel=True)`); on client disconnect it calls `agent.cancel_pending` / `discard_pending` so abandoned approvals never pin a thread.
3. **`backend/agent.py` → `ConversationAgent.chat_stream`**: exactly **one** LLM call per message (tools `create_invoice`, `create_sales_order`, `lookup_records`, `ask_clarification`, `refuse_request`, temperature 0). If the previous reply was a numbered "which one?" question and the user answers with a number/name, `_take_choice` continues that request **without** calling the LLM. `_map_intent` validates the AI's arguments and turns them into an internal `odoo_create` / `odoo_search_read` request; result/error texts are written by code (`_summarize_result`), never by a second LLM call.
4. **`backend/resolver.py`** (backend-owned): names → Odoo ids. Exact name (`=ilike`) wins, else one partial match, else retry without trailing "s"; several matches raise `AmbiguousName` (numbered list, user picks); internal contacts (own company, internal users) are excluded; for an unknown **product** an optional `suggest` callback (`agent._suggest_product`, a second LLM call constrained by a JSON-schema enum of real product names) can offer one candidate – still confirmed by the user. `prepare_review` adds Odoo list prices, total excl. VAT and a duplicate warning for the approval card.
5. Approval: `chat_stream` blocks on a `threading.Event` (expires after `APPROVAL_TIMEOUT_SECONDS`).
6. **`backend/odoo_client.py`** is the only code that talks to Odoo and the place where safety is enforced regardless of the AI: per-thread XML-RPC connections with timeouts; `READ_RULES` allow-list (partners, products, quotations, customer invoices; row limit); `CREATE_RULES` (only draft `sale.order` and `account.move` with `move_type=out_invoice`, known fields only, `price_unit` dropped unless `ODOO_ALLOW_AI_PRICES=true`); Odoo tracebacks reduced to one line; `localhost` rewritten to `127.0.0.1` (2 s per connection on Windows otherwise).
7. **`backend/audit.py`**: append-only `Application/V3.1/logs/audit.jsonl` (`ai_tool_call`, `approval_*`, `created`, `create_blocked`, `read_blocked`, `product_suggestion`, `chat_timing`). First place to look when the real model misbehaves.

### Invariants to keep
- The AI sends **names and quantities only** – never Odoo ids or prices; ids and prices always come from Odoo.
- Keys starting with `_` (e.g. `_resolved_partner_id_name`, `_resolved_product_id_price`) are for the card only; `execute_create` strips them before Odoo.
- A `ValueError` raised during resolution is the user-facing message path (`OdooError` subclasses `ValueError` for this reason) – nothing is created.
- No "confirm order", "post invoice", update or delete actions (team decision; the `ai_agent` Odoo user could technically post invoices).
- `agent.py` ownership: AI prompt/calls/streaming = AI & chat owner; resolution/validation/approval/Odoo = backend owner (see `documentation/our-work/decisions/DECISIONS.md`).

## Tests
`Application/V3.1/tests/fake_ollama.py` is a scripted Ollama stand-in (HTTP `/api/chat`) whose replies are keyed on words in the user message; it reproduces real llama3.1 mistakes (lists sent as text, odd limits, plural names). Add a trigger there when a new real-model behaviour needs coverage. Tests that wait on approvals monkeypatch `agent.APPROVAL_TIMEOUT_SECONDS` so a regression fails fast instead of hanging. The scripted AI does not test AI quality – real-model checks go in the experiment log.

## Documentation conventions (`documentation/README.md` is the index)
- `documentation/previous-group/` is an archive – don't add to it.
- Every PR adds an entry to `documentation/our-work/changes/CHANGELOG.md`.
- Test runs → `documentation/our-work/tests/TEST-RESULTS.md` (+ report from `Setup/run_tests.py`); measurements/real-AI findings → `documentation/our-work/experiments/EXPERIMENT-LOG.md`; decisions → `documentation/our-work/decisions/DECISIONS.md`.
- Work on a branch and merge to `main` via pull request.
- PRD and blueprint: `documentation/our-work/design/PRD.md` and `BLUEPRINT.md` (Anastasia's text, the reference; replaces the previous group's `prd.md`) with readable HTML versions `PRD.html` and `BLUEPRINT.html` next to them: change both together. Build plan: `documentation/our-work/planning/BUILD-PLAN.html`; tasks are ticked in its `PLAN` data block. Changes to the PRD or the build plan are logged in `DECISIONS.md` with the reason.

## Build workflow (agreed with the supervisor, 16 Nov 2026)
- Work in phases from the build plan (`planning/BUILD-PLAN.html`); each phase ends with a **test gate** (`pytest Application/V3.1/tests`, plus `npm run lint && npm run build` if the UI changed).
- Commit and push only when the gate passes, and push after every phase so teammates can pull the latest before they start.

## Reports for people
- Reports, overviews and status pages meant for humans (team, supervisor) are a single self-contained HTML page: D3 for charts, Three.js for 3D/visual pieces, Motion (motion.dev) for animation, loaded from a CDN. Include diagrams, flowcharts and animated or interactive demos (e.g. step through the request flow).
- Numbers and claims come from the Markdown records above (CHANGELOG, TEST-RESULTS, EXPERIMENT-LOG, DECISIONS), which stay the source of truth; never invent data for a chart.
