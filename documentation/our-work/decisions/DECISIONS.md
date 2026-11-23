# Decisions

One line per decision, so we don't discuss the same thing twice. Newest first.
When a data-contract decision is made, also tick it in [DATA-CONTRACT.md](../design/data-contract/DATA-CONTRACT.md).

## Decided
| Date | Decision | Why | Alternatives considered | Who |
|---|---|---|---|---|
| 2026-11-23 | Anastasia's PRD and blueprint (`design/PRD.md`, `BLUEPRINT.md`, v1.1 with review changes) are the reference, with HTML versions next to them; our earlier HTML PRD and blueprint are dropped; the build plan moves next to them in `design/` and follows the blueprint's delivery sequence | One PRD and one blueprint; hers knows the charter (MCP, >90%); the previous group's `prd.md` promised features that were never built | Keep two sets; keep our HTML PRD | Floyd |
| 2026-11-16 | Start testing with entrepreneurs now (a few demos, in person and via LinkedIn) instead of waiting until the product is finished | Supervisor: validate the ~80% that is built before over-investing in the last 20% | Finish first, test at the end | Team + supervisor |
| 2026-11-16 | Build in phases from a build plan; every phase ends with a test gate and is pushed only when the tests pass | No broken code on GitHub; teammates always pull a working version | Push whenever | Team + supervisor |
| 2026-11-16 | Reports for people are interactive HTML pages (D3, Three.js, Motion); the Markdown files stay the record | Supervisor: documentation must be readable for humans, not just AI | Markdown/PDF only | Team + supervisor |
| 2026-11-16 | For an unknown product name the AI may **suggest** one real product; the user must confirm it (reply 1 / the name) and then approve the card | "premium chair" → Ergonomic Chair is a sensible guess, but a guess must never become an order on its own | No suggestions; accept the AI's guess automatically | Floyd |
| 2026-11-16 | Duplicate check **warns** on the approval card (same customer + same amount in 24 h), never blocks. **Team may still change it.** | Repeat orders are normal; a human decides | Block duplicates | Floyd |
| 2026-11-16 | Own company and internal users are never matched as customers | A request could otherwise be addressed to "My Company" | Only customers with sales history (would hide new customers) | Floyd |
| 2026-11-16 | Ollama keep-alive default 1 h (24 h on the demo PC) | Cold start ~40–45 s vs 2–3 s warm (experiment 12) | Per-PC setting only | Floyd |
| 2026-11-16 | D3 name matching implemented with the recommended default: exact name (any case) wins; one partial match is used; several matches → ask the user. **Team may still change it.** | The old code silently used the first partial match ("Jansen" → one of two customers) | Ask on every partial match | Floyd |
| 2026-11-12 | Our version lives in `Application/V3.1`; the previous group's V3 stays unchanged; `V4` is reserved for the redesign | Clear before/after comparisons; V3.1 = hardened V3, V4 = new design | Rename to V4 now; keep editing V3 in place | Floyd |
| 2026-11-12 | Odoo 20 Community, database `odoo`, Sales + Invoicing, Netherlands, no demo data, limited `ai_agent` user | Same setup for everyone; AI never runs as administrator | Odoo 19; admin login | Floyd |
| 2026-11-12 | Prices always come from Odoo (`ODOO_ALLOW_AI_PRICES=false`) | AI-invented prices were accepted before (10.00 vs 50.00) | Trust the AI's price | Floyd |
| 2026-11-12 | No "confirm order" / "post invoice" actions for now | `ai_agent` is technically allowed to post invoices; a posted invoice can't simply be deleted | Allow with approval | Floyd |

## Open – to decide in the Floyd/Marija meeting
| Topic | Recommendation (see [HANDOFF-MARIJA.md](../planning/HANDOFF-MARIJA.md)) |
|---|---|
| MCP approval (proposed 23 Nov, for the supervisor review) | No `approve_draft` tool for an AI: a person approves in the review screen or through a client confirmation the model cannot answer. Reason: an assistant that can approve can approve its own draft |
| Definition-of-done ranking (proposed 23 Nov, confirm against the charter) | Must: draft flow, >90% evaluation, MCP with human approval, reviewed docs. Should: traceability. Could: log-in and roles, before real customer data |
| Branch plan | Short branches from `main`, every change via a PR reviewed by the other; protect `main` (1 approval) |
| Ownership of `agent.py` | Floyd first moves resolution/validation/approval into own files (no behaviour change), then Marija owns the rest |
| Data contract D1, D3, D4, D5, D8, D10 | See the recommendations in the handoff |
| Approval box content | Backend sends lines (product × qty @ Odoo price), total excl. VAT, warnings; chat shows all of it |
| Model choice | Compare llama3.1, qwen3:8b and one small model on the same test set (keep-alive is decided, see above) |
| Test-set format | One row per prompt, based on `contract_examples.json` |
| When to start V4 | Copy V3.1 → V4 when the contract work starts; freeze V3.1 |
