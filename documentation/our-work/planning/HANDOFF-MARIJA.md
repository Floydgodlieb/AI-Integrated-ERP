> **12 Nov 2026.** Handoff from Floyd (backend) to Marija (AI & chat). Decisions from the follow-up meeting go into [DECISIONS.md](../decisions/DECISIONS.md).

# Handoff for Marija (AI & Chat) – state on 12 Nov 2026

From Floyd (backend). Three parts: **what changed and was tested**, **what you can start on now**, and **what we must decide together first**.

## TL;DR
- The backend (Odoo connection, safety rules, approvals, audit log) has been reworked and tested: **41 automated tests pass** on Linux and on Floyd's Windows PC, and the real `llama3.1` works with it.
- Our code now lives in **`Application/V3.1`** (pull request #2); `Application/V3` is the previous group's original, kept unchanged for before/after comparisons. **Always work in V3.1.**
- It is **merged into `main`** (pull request #1). Your branch `marija-ai-chat` is still the old `main`: **move it onto the new `main`** (commands in §4) so you don't edit an old version of `agent.py`.
- You can start right away on the chat screen and on the AI calls (§2). The data contract and the approval box content need a short meeting first (§3).
- Full details: `documentation/our-work/changes/BACKEND-CHANGES.md` (has a section "For Marija"). All measurements so far: `documentation/our-work/experiments/EXPERIMENT-LOG.md` – please add your experiments there too.

---

## 1. What Floyd changed and tested

### Changes (backend only; the AI prompt and chat screen were not touched)
| Change | Evidence |
|---|---|
| One Odoo connection per thread + timeouts | 40 parallel requests: **28 failed → 0 failed** |
| Odoo connection via `127.0.0.1` instead of `localhost` (automatic) | Floyd's Windows PC: **2.08 s → 0.03 s per new connection** |
| Short error messages (no tracebacks/server paths) | The 2 KB Odoo traceback → `ValueError: Invalid field '[' on 'res.partner'` |
| Read allow-list (customers, products, quotations, customer invoices), max 50 rows; lists sent as text are understood | `res.users` / system settings refused. **llama3.1's "fields as text" failure is fixed in the backend** |
| Create allow-list: only **draft** quotations and **draft** customer invoices, known fields, quantity > 0, real Odoo ids | AI's `"state": "sale"` and extra fields are dropped and reported |
| **Prices come from Odoo**, not from the AI (`ODOO_ALLOW_AI_PRICES=false`) | AI price 10.00 → Odoo price 50.00 |
| Approvals expire after 5 min and are released when the browser closes | 45 abandoned approvals: **server froze → keeps working** |
| Audit log `Application/V3.1/logs/audit.jsonl` | Every approval, create and refused request |
| Launcher: local-only by default (`UI_ON_NETWORK=1` to open), works on Windows/macOS/Linux | No more `Network: http://192.168…` |
| Setup scripts in `Setup/`, pinned packages, `.env.example` cleaned | Teammates don't need the zip anymore |

### What the AI now receives from the backend (important for your prompts)
- Errors: `{"error": "short readable message"}`
- Create success: `{"status": "success", "created_id": 3, "state": "draft"}` + optional `"ignored_fields": [...]`, `"note": "Prices were taken from Odoo, not from the request."`
- Approval outcomes: `{"status": "cancelled", ...}` or new `{"status": "expired", "message": "No approval was given in time. Nothing was created."}`
- Refused read: `{"error": "Reading 'res.users' is not allowed. Allowed: ..."}`

### Tests done
**Automated:** 41 tests in `Application/V3.1/tests/` (offline rules, real Odoo, full API with a scripted AI stand-in that reproduces llama3.1's mistakes). Pass on Linux (Python 3.11 + 3.13) and on Floyd's Windows PC (Python 3.12, Odoo 20.0.20261109).

**By hand, with the real `llama3.1` on Floyd's PC** (RTX 3070 Ti, Ryzen 5 5600X, 64 GB):
| # | Test | Result |
|---|---|---|
| 1 | Ollama cold vs warm, tiny prompt | ~40 s cold, ~1 s warm |
| 2 | **Old** V3: "Show me all customers" | ❌ AI sent fields as text → Odoo error → **AI invented customers** (John Doe…) |
| 5 | `localhost` vs `127.0.0.1` | 2.08 s vs 0.03 s per connection; a test went from 204 s → 15 s |
| 6 | **New** backend: "Show me all customers" | ✅ real 17 contacts, AI text matched; ~45 s **cold** |
| 7 | Same, model already loaded | ✅ almost instant |
| 8 | "Create a sales order for Pepsi with 2 Chair" + approve | ✅ draft quotation created |
| 9 | "Create an invoice for Pepsi with 3 Chair" + approve | ✅ draft invoice; backend dropped an extra `name` field and the AI reported it |
| 10 | Prices in Odoo | ✅ 3 × 50.00 = 150.00 excl. tax, 181.50 incl. 21% VAT (also when the AI sent 10.00) |
| 12 | `OLLAMA_KEEP_ALIVE=24h` (keep model loaded), first message after 10+ min idle | ✅ **2–3 s instead of ~40–45 s**. `ollama ps`: 100% GPU, 5.3 GB, context 4096 |

**Main lesson:** with a warm model the whole chain is almost instant; the big delay was the **cold start (~45 s)** when Ollama unloads the model after 5 idle minutes. Keeping the model loaded brought it to **2–3 s** – but today that is only a setting on Floyd's PC (task 4 makes it permanent in code).

---

## 2. What you can start on now (no decisions needed)

Files are yours unless marked *shared*. In `agent.py` Floyd only changed the approval part (≈ lines 290–330); please don't rewrite that block without talking.

| Priority | Task | Where | Why / evidence |
|---|---|---|---|
| 1 | **Fix lost line breaks** in answers | `chat-UI/src/Chat.jsx` (SSE parsing, ~line 98–106): an event can have **several `data:` lines**; join them with `\n` instead of reading only the next line | Every list from the AI shows as one long line |
| 2 | **Approval box shows the full text** | `chat-UI/src/Chat.css` `.confirm-detail`: remove `white-space: nowrap; overflow: hidden; text-overflow: ellipsis;`, widen `.confirm-dialog` | In the real test it showed only "Create Invoice \| Customer: Pepsi \| 1 in…" |
| 3 | **Stop the AI from inventing answers after a failed request** | *shared* `agent.py`, right after the tool loop: if *all* tool results this turn are errors, write the answer in code ("I couldn't do that: …, nothing was changed") instead of the 2nd AI call; add "never invent data" to the prompt | Test 2: invented customers. The backend now gives short errors, but the 2nd AI call can still improvise |
| 4 | **Model name + keep-alive as settings** | *shared* `agent.py` two `ollama_chat(model='llama3.1', …)` calls (~lines 268 and 352) → `OLLAMA_MODEL`, `OLLAMA_KEEP_ALIVE` from `.env`; pass `keep_alive=` | Needed for the model comparison; **experiment 12: cold start 40–45 s → 2–3 s** – put it in code so it works on every PC |
| 4b | **Long chats vs. the 4,096-token context** | *shared* `agent.py` (history sent on every call) | `ollama ps` shows context 4096: in long chats the oldest messages silently drop out. Trim the history or raise `num_ctx` (costs GPU memory) |
| 5 | **Clear result messages instead of grey "Executed"** | `Chat.jsx` `DataTable` fallback | Created / refused / expired / error should be readable ("Created draft quotation #3") |
| 6 | Placeholders and lint | `Chat.jsx` header "Your Model / YourERP / YourAIModel"; 2 ESLint errors (empty `catch`, lines ~113, 118) | Polish for the demo |
| 7 | Dev proxy to `127.0.0.1` | `chat-UI/vite.config.js`: `'/api': 'http://127.0.0.1:8001'` | Same Windows `localhost` delay as Odoo had |
| 8 | **First AI experiment**: can llama3.1 fill the draft schema with Ollama structured output? | `documentation/our-work/design/data-contract/` (`schemas_draft.py`, 9 examples in `contract_examples.json`, see `DATA-CONTRACT.md` §5) | Decides the design of the contract; log accuracy + seconds |
| 9 | **Model comparison**: `llama3.1` vs `qwen3:8b` (both fit the 8 GB GPU) on the same 9 prompts | your own script | % valid JSON, % right action, seconds per answer (warm and cold) |

For testing without a GPU or without waiting for the model, `Application/V3.1/tests/fake_ollama.py` is a scripted stand-in you can extend.

---

## 3. What we must decide together first (45-minute meeting, Floyd + Marija; Tijn/Anastasia welcome)

1. **Branch plan.** Floyd's work is already merged into `main` (PR #1, merged before review – please still look through it on GitHub and leave comments; fixes go in a new PR). From now on: both work on short branches from `main`, every change via a pull request reviewed by the other.
2. **Who owns what in `agent.py`.** Proposal: Marija = prompt, AI calls, streaming, answer texts; Floyd = name resolution, validation, approval flow, Odoo calls. Long term: move Floyd's parts out of `agent.py` into their own files (`resolver.py`, …) so we stop editing the same file.
3. **Data contract D1–D12** (`documentation/our-work/design/data-contract/DATA-CONTRACT.md`): especially
   - D1 AI sends names, backend resolves ids
   - D3 exact name match wins; ambiguous → ask the user ("did you mean Jansen Bouw or Jansen & Zonen?")
   - D4 prices from Odoo by default (already built); when is an AI price allowed?
   - D5 new customers: never via AI in v1? (the `ai_agent` user can't create them)
   - D8 reads as named queries instead of free Odoo models
   - D10 where the schema lives and who may change it
4. **Approval box content** (who builds what): backend produces the lines (product × qty @ Odoo price, totals, warnings), chat shows them. Agree the exact shape (`needs_approval` in the contract draft).
5. **Name matching (stage 7) and duplicate check (stage 8):** block or warn, and how the chat shows a "did you mean…?" question or a duplicate warning. Floyd builds the backend once this is decided.
6. **Model and keep-alive:** keep-alive in the app's code (task 4) vs. per-PC setting; which models to compare; when we switch.
7. **Testing:** backend tests use the scripted AI; AI quality needs a real-model test set (Anastasia's 50 prompts). Agree the format so your experiment script and her test set fit.
8. **Your hardware:** Floyd's numbers are from an RTX 3070 Ti (8 GB). If your PC has no NVIDIA card with ~8 GB, `llama3.1` will be much slower for you – then model choice (task 9) becomes urgent. Measure the same two numbers (cold/warm) and add them to the experiment log.
9. **Still open for the whole team:** revoke the leaked Odoo password/Teams webhook (old V1/V2 code); email the previous group; **don't add "confirm order" or "post invoice" actions yet** (the `ai_agent` user is technically allowed to post invoices, and a posted invoice can't simply be deleted).

---

## 4. How Marija gets started (Windows, Command Prompt)
First set up everything with `Setup/Quickstart.md` (Odoo, seed data, `.env`, Ollama + `llama3.1`). Then, in the repo folder:
```
git fetch origin
git checkout -B marija-ai-chat origin/main
git push -u origin marija-ai-chat --force-with-lease
```
(`marija-ai-chat` has no commits of its own yet, so this only moves it onto the new `main`. **Skip these three lines if you already made commits on it** – then ask Floyd to help merge.)
```
.venv\Scripts\python.exe -m pip install -r Application\V3.1\requirements-dev.txt
.venv\Scripts\python.exe -m pytest Application\V3.1\tests -v
```
Expected: 41 passed (Odoo must be running; the tests create a few draft records). Then start the app: `cd Application\V3.1` and `..\..\.venv\Scripts\python.exe main.py`.
