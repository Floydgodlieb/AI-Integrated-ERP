# Decisions

One line per decision, so we don't discuss the same thing twice. Newest first.
When a data-contract decision is made, also tick it in [DATA-CONTRACT.md](../design/data-contract/DATA-CONTRACT.md).

## Decided
| Date | Decision | Why | Alternatives considered | Who |
|---|---|---|---|---|
| 2026-11-12 | Our version lives in `Application/V3.1`; the previous group's V3 stays unchanged; `V4` is reserved for the redesign | Clear before/after comparisons; V3.1 = hardened V3, V4 = new design | Rename to V4 now; keep editing V3 in place | Floyd |
| 2026-11-12 | Odoo 20 Community, database `odoo`, Sales + Invoicing, Netherlands, no demo data, limited `ai_agent` user | Same setup for everyone; AI never runs as administrator | Odoo 19; admin login | Floyd |
| 2026-11-12 | Prices always come from Odoo (`ODOO_ALLOW_AI_PRICES=false`) | AI-invented prices were accepted before (10.00 vs 50.00) | Trust the AI's price | Floyd |
| 2026-11-12 | No "confirm order" / "post invoice" actions for now | `ai_agent` is technically allowed to post invoices; a posted invoice can't simply be deleted | Allow with approval | Floyd |

## Open – to decide in the Floyd/Marija meeting
| Topic | Recommendation (see [HANDOFF-MARIJA.md](../planning/HANDOFF-MARIJA.md)) |
|---|---|
| Branch plan | Short branches from `main`, every change via a PR reviewed by the other; protect `main` (1 approval) |
| Ownership of `agent.py` | Floyd first moves resolution/validation/approval into own files (no behaviour change), then Marija owns the rest |
| Data contract D1, D3, D4, D5, D8, D10 | See the recommendations in the handoff |
| Approval box content | Backend sends lines (product × qty @ Odoo price), total excl. VAT, warnings; chat shows all of it |
| Name matching / duplicate check | Ambiguous names: ask; duplicates: warn, don't block |
| Model and keep-alive | Keep-alive in code (default 1 h, demo PC 24 h); compare llama3.1, qwen3:8b and one small model on the same test set |
| Test-set format | One row per prompt, based on `contract_examples.json` |
| When to start V4 | Copy V3.1 → V4 when the contract work starts; freeze V3.1 |
