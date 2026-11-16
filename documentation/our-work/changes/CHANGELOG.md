# Changelog – all changes since we took over

Newest first. **Every pull request adds an entry here** (what changed, why, evidence, PR link).
Technical detail of the backend work: [BACKEND-CHANGES.md](BACKEND-CHANGES.md). Measurements: [EXPERIMENT-LOG.md](../experiments/EXPERIMENT-LOG.md). Test runs: [TEST-RESULTS.md](../tests/TEST-RESULTS.md).

## At a glance: previous group's V3 → our V3.1
| Topic | V3 (previous group, `Application/V3`) | V3.1 (ours, `Application/V3.1`) |
|---|---|---|
| Several users at once | 28 of 40 parallel requests failed | 0 of 40 fail |
| Browser closed during approval | Server froze after 40 abandoned approvals | Approval released at once; unanswered approvals expire after 5 min |
| What the AI can read | Any Odoo model, incl. system settings; all records | Customers, products, quotations, customer invoices; max 50 rows |
| What the AI can create | Any model, any fields | Only draft quotations and draft customer invoices, known fields only |
| Prices | Whatever the AI sends | Always from Odoo (verified: 3 × 50.00) |
| Odoo errors | 2 KB traceback with server paths, hidden from the user | One short readable line |
| AI user | Ran as the Odoo administrator | Limited `ai_agent` user |
| Audit trail | None | `Application/V3.1/logs/audit.jsonl` |
| Network exposure | Chat open to the whole Wi-Fi | Local only by default |
| Windows speed | `localhost`: +2 s per new Odoo connection | `127.0.0.1`: 0.03 s |
| Tests | None | 41 automated tests |
| Setup | Undocumented | `Setup/` scripts + quickstart, reproducible test data |

Not changed yet (AI & chat side, data contract): see "Not done yet" in [BACKEND-CHANGES.md](BACKEND-CHANGES.md).

---

## Approval card with Odoo prices, duplicate warning, and fixes from Floyd's real-AI test (open PR)
- **Bug fix (seen with the real llama3.1):** "I want to sell 3 chairs to Acme" kept answering *"Which product and quantity should I include?"*. Small models send the product lines in other shapes (as text, as one entry without a list, quantity as `"3"`) or in the plural ("chairs"). The backend now accepts these shapes and retries a name without its trailing "s". Each raw AI call is written to the audit log (`ai_tool_call`) so the next failure shows what the model sent.
- **Approval card shows money:** each line as product × quantity @ Odoo list price = subtotal, plus the total excl. VAT. Prices are read from Odoo, never taken from the AI.
- **Duplicate warning (stage 8):** a draft for the same customer with the same amount in the last 24 hours → warning on the card; approving is still possible.
- **Own company and internal users** (My Company, Administrator, AI Agent, OdooBot) can no longer be matched as customers.
- **Keep-alive default 1 h** (code and `.env.example`): no ~40 s cold start after 5 idle minutes on any PC.
- **`backend/resolver.py`:** the name-matching code moved out of `agent.py` (no behaviour change), so Floyd's and Marija's code are in separate files.
- Docs: manual test checklist for Anastasia (`tests/MANUAL-TEST-CHECKLIST.md`); Marija's weekly report moved to `planning/weekly-reports/`; branches `marija-ai-chat` and `marija-weekly-task` are fully merged and can be deleted on GitHub.

## Name matching: ask instead of guessing ([#5](https://github.com/Floydgodlieb/AI-Integrated-ERP/pull/5), merged 16 Nov 2026)
- `agent.py` `resolve_entities`: an exact name (any case) wins; otherwise a single partial match is used (the approval card shows the full Odoo name); several matches → the user gets a numbered list and **picks one by replying with the number or the name**; the same request then continues without asking the AI again (anything else counts as a new request). Before: the first partial match was silently used.
- 12 new tests (`test_name_matching.py`; end-to-end via Marija's `create_invoice` action: ambiguous name asked, pick by number, pick by name, other reply = new request). 4 fail on the old code. 53 tests pass.

## Marija – V3.1 chat and structured AI actions (pushed directly to `main`, 14 Nov 2026, `9c8aae2`)
- One structured AI action per message (names and quantities only, no ids or prices); one AI call per message; result and error texts written by the app; line breaks fixed; approval card with customer and product lines; model settings, timing records, extraction replay script. Details: [her weekly report](../planning/weekly-reports/2026-11-14-MARIJA.md).

## PR #3 – Documentation restructure, test results, changelog (merged 12 Nov 2026)
- `documentation/` split into `previous-group/` (their documents, content untouched, clean file names) and `our-work/` (handover, planning, changes, tests, experiments, design, decisions).
- New: this changelog, [TEST-RESULTS.md](../tests/TEST-RESULTS.md) with raw reports in `tests/runs/`, [DECISIONS.md](../decisions/DECISIONS.md) template, `documentation/README.md` index.
- Added from the handover: handover report, session overview, team plan, roles & tasks, project overview, Marija's handoff (marked as dated snapshots).
- New script `Setup/run_tests.py`: runs all tests and saves the report as evidence.
- All links updated.

## PR #2 – Previous group's V3 restored; our version becomes V3.1 (merged 12 Nov 2026)
[Floydgodlieb/AI-Integrated-ERP#2](https://github.com/Floydgodlieb/AI-Integrated-ERP/pull/2)
- `Application/V3` restored byte-for-byte from the previous group's last commit (`0fba0a4`) as an archive for before/after comparisons.
- Our hardened version moved to `Application/V3.1`; all paths in scripts, guides, tests and docs updated; README gets a "Versions" table.
- `V4` kept free for the planned redesign (data contract, structured AI output, new approval flow).
- Evidence: 41 tests pass from `Application/V3.1`; V3 verified identical to the original.

## PR #1 – Backend hardening, setup scripts, experiment log (merged 12 Nov 2026)
[Floydgodlieb/AI-Integrated-ERP#1](https://github.com/Floydgodlieb/AI-Integrated-ERP/pull/1) – 8 commits:
| Commit | Change |
|---|---|
| `3bff41c` | Setup scripts (`seed_odoo.py`, `check_setup.py`, `docker-compose.yml`, `ODOO-SETUP.md`) and draft data contract added to the repo |
| `24c44d3` | Backend hardening: connection per thread + timeouts, short errors, read/create allow-lists, prices from Odoo, expiring approvals, audit log, safer launcher, pinned packages |
| `a798ff4` | 40 automated tests (offline rules, Odoo integration, end-to-end API with a scripted AI) |
| `b17d27a` | `BACKEND-CHANGES.md`, quickstart updated |
| `7a62a3a` | Test fix: approval prompt split over network chunks on Windows; fail fast instead of hanging |
| `69e5f4f` | Odoo via `127.0.0.1` instead of `localhost` (2.08 s → 0.03 s per connection on Windows) + 1 test |
| `6df3754` | Approval-box problem from the first real-AI test documented as a task for Marija |
| `29be488` | Shared experiment log (experiments 1–12); outdated setup zip removed |

## Before the pull requests (10 Nov 2026, Floyd, directly on `main`)
- `0c99260` Quickstart for teammates; `3f4a997` setup-kit zip (later replaced by the scripts in `Setup/`).

## Starting point: previous group (Feb–Jun 2026)
V1 → V2 → V3 (last commit `0fba0a4`, 12 Jun 2026). What they built and how it worked: [HANDOVER-REPORT.md](../handover/HANDOVER-REPORT.md).

---

## How to add an entry
Add a section at the top (under "At a glance") for every pull request:
```
## PR #N – short title (merged <date>)
[link to the PR]
- what changed (one line per change)
- why / evidence (test result or experiment number)
```
