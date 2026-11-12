# Experiment log

One entry per experiment: **what we expected → what we changed → what we measured → what we learned.**
This log is part of our grading evidence (growth, learning, experimentation), so add every experiment, including the failures.

**How to add an entry:** copy the template at the bottom, give it the next number, fill in all columns, commit.
Always write **where** it was measured (whose PC / which environment) and whether the **real AI** or the **scripted stand-in** (`Application/V3/tests/fake_ollama.py`) was used.

## Environments
| Code | What |
|---|---|
| **F-PC** | Floyd's PC: Windows 10, Ryzen 5 5600X, 64 GB RAM, RTX 3070 Ti (8 GB), Python 3.12.10, Odoo 20.0.20261109 Community (Windows installer), Ollama 0.40.16, `llama3.1` (8B, 5.3 GB, 100% GPU, context 4096) |
| **LAB** | Linux test machine used during the handover analysis: Odoo 19.0 / 20.0 Community in Docker, Python 3.11 + 3.13. **No real AI** – scripted stand-in only |

## Entries

| # | Date | Who / where | Question / hypothesis | Change or setup | Measurement | Result | What we learned / next |
|---|---|---|---|---|---|---|---|
| 1 | 10 Nov | Floyd / F-PC, real AI | How fast is `llama3.1` on our hardware? | `ollama run llama3.1 "Say hello in five words"`, twice | Stopwatch | **Cold ~40 s, warm ~1 s** | The first call after loading is the slow part; model loading dominates |
| 2 | 10 Nov | Floyd / F-PC, real AI | Does the previous group's V3 work with the real model? | Original V3, "Show me all customers" | Raw API output via `curl` | ❌ AI sent the field list as **text** → Odoo error `Invalid field '['` → second AI call **invented customers** (John Doe, Jane Smith…; another run: Pepsi, Coca-Cola, McDonald's) | The AI must never be the source of facts; errors must not be "interpreted" by the AI. Led to entries 4–6 |
| 3 | 9 Nov | LAB, scripted AI | Is the old backend safe with several users / abandoned approvals? | 40 parallel chats; 45 chats closed during approval | Count of failures; does a new chat still answer? | **28 of 40** parallel requests failed; after 40 abandoned approvals **every new chat hung** | Shared Odoo connection isn't thread-safe; approvals blocked threads forever |
| 4 | 12 Nov | LAB + F-PC, scripted AI | Do the backend changes fix entries 2–3? | Branch `claude/gifted-mccarthy-r2p1hv` (see `documentation/BACKEND-CHANGES.md`) | 40 automated tests (Python 3.11, 3.12, 3.13) | ✅ 40/40 pass; parallel **28 failed → 0**; "fields as text" now handled by the backend; AI price 10.00 → **Odoo price 50.00** | Safety rules belong in the backend, not in the prompt |
| 5 | 12 Nov | Floyd / F-PC | Why does one test take 204 s on Windows (1 s on Linux)? Hypothesis: `localhost` tries IPv6 first | Timed a new Odoo connection via `localhost` and via `127.0.0.1` | Python timing | **2.08 s vs 0.03 s** per new connection; after switching to `127.0.0.1`: test **204 s → 15 s** | On Windows always use `127.0.0.1`. Now automatic in the backend (+1 test, 41 total) |
| 6 | 12 Nov | Floyd / F-PC, real AI | Does the hardened backend work with the real model? | "Show me all customers" in a new chat | Stopwatch + compare with Odoo | ✅ Real list of 17 contacts, AI text matched; **~45 s** (model was cold) | Correctness fixed; latency is the model loading, see 7 and 12 |
| 7 | 12 Nov | Floyd / F-PC, real AI | Is the 45 s the model loading? | Same request again immediately | Stopwatch | **Almost instant** | Yes: once loaded, AI + backend + Odoo answer in about a second |
| 8 | 12 Nov | Floyd / F-PC, real AI | Can the real model create a quotation through the approval flow? | "Create a sales order for Pepsi with 2 Chair" + approve | Check in Odoo | ✅ Draft quotation created (almost instant, model warm) | The approval flow works end to end with the real model |
| 9 | 12 Nov | Floyd / F-PC, real AI | Same for an invoice | "Create an invoice for Pepsi with 3 Chair" + approve | Check in Odoo | ✅ Draft invoice; the backend dropped an extra `name` field and the AI reported it. ⚠️ Approval box text cut off ("Create Invoice \| Customer: Pepsi \| 1 in…") and shows no product/qty/price. ⚠️ AI wrote "Invoice Number: (Untitled)" (invented) | Approval box must show everything that is approved → task for Marija. Return Odoo's real record name in the create result |
| 10 | 12 Nov | Floyd / F-PC | Do prices come from Odoo, also when the AI sends its own? | Inspect the 3 draft invoices (2 from tests where the AI sent 10.00, 1 from the chat) | Odoo invoice list | ✅ All **150.00 excl. tax / 181.50 incl. 21% VAT** (= 3 × 50.00) | Price rule works with the real model and Dutch VAT |
| 11 | 12 Nov | Floyd / F-PC | Who made the empty quotation S00001 (Acme BV)? | Odoo chatter of S00001 | – | Created by **Administrator** (a human), empty; not the AI (that would show "AI Agent") | The separate `ai_agent` user makes AI actions traceable |
| 12 | 12 Nov | Floyd / F-PC, real AI | Does keeping the model loaded remove the cold start? | `setx OLLAMA_KEEP_ALIVE 24h`, restart Ollama; `ollama ps` shows "24 hours from now", 100% GPU, 5.3 GB | First chat message after 10+ min idle, stopwatch | ✅ **2–3 s instead of ~40–45 s** | Biggest latency win so far. Make it permanent in code (`keep_alive` in the AI call) so it works on every PC. Costs 5.3 GB of GPU memory while loaded |

## Open questions (next experiments)
- Can `llama3.1` fill the draft data-contract schema with Ollama structured output? (`documentation/data-contract/DATA-CONTRACT.md` §5)
- `llama3.1` vs `qwen3:8b` on the same prompts: % valid output, % right action, seconds (warm and cold).
- How do long chats behave with the 4,096-token context?
- Same measurements on each teammate's PC (hardware differs).

## Template
| # | Date | Who / where | Question / hypothesis | Change or setup | Measurement | Result | What we learned / next |
|---|---|---|---|---|---|---|---|
| 13 | | | | | | | |
