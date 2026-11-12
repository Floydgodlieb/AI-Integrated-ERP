# Test results

Two kinds of evidence:
1. **Automated tests** (`Application/V3.1/tests/`, 41 tests). The AI is a **scripted stand-in** (`tests/fake_ollama.py`) that reproduces llama3.1's real mistakes – so these test the backend, not the AI's quality.
2. **Manual tests with the real AI** (`llama3.1` via Ollama), checked against Odoo.

Measurements and what we learned from them are in the [experiment log](../experiments/EXPERIMENT-LOG.md); this file is the test record.

## How to run and record a test run
From the repo folder (Odoo running with the seed data, `Application\V3.1\.env` filled in):
```
.venv\Scripts\python.exe Setup\run_tests.py --who yourname
```
It saves the full report in [`runs/`](runs/) and prints a table row – paste that row into the table below and commit both.
(The tests create a few draft quotations/invoices in your Odoo database.)

## What the 41 automated tests cover
| File | Tests | Needs Odoo? | What |
|---|---|---|---|
| `test_safety_rules.py` | 22 | No | Error cleaning, lists sent as text, price rule, only customer invoices, quantity/customer/line checks, unknown fields dropped, forbidden models refused, `localhost` → `127.0.0.1`, unreachable Odoo |
| `test_odoo_client.py` | 9 | Yes | 40 parallel reads, seed data present, "fields as text", forbidden fields/filters, row limit, short Odoo errors, invoice priced by Odoo, order stays draft |
| `test_api.py` | 10 | Yes | Full chain browser → API → agent → scripted AI → Odoo: health, reads, refused reads, approve/decline, unknown customer, 20 parallel chats, 45 abandoned approvals, approval expiry |

Without Odoo running, the 19 Odoo tests are skipped and the 22 offline tests still run.

## Automated test runs
| Date | Who | OS | Python | Odoo | Commit | Result | Report |
|---|---|---|---|---|---|---|---|
| 2026-11-12 14:33 | lab-linux | Linux | 3.13.18 | 20.0-20261102 | `4751804` | ✅ 41 passed in 15.10s | [report](runs/2026-11-12_1433_lab-linux.txt) |
| 2026-11-12 | lab | Linux | 3.13 | 20.0-20261102 | `31838c8` | ✅ 41 passed (from `Application/V3.1`, after the move) | – |
| 2026-11-12 | lab | Linux | 3.13 | 20.0-20261102 | `69e5f4f` | ✅ 41 passed (after the `localhost` fix) | – |
| 2026-11-12 | floyd | Windows 10 | 3.12.10 | 20.0.20261109 | `b17d27a` | ✅ 40 passed (abandoned-approvals test very slow, see below) | – |
| 2026-11-12 | lab | Linux | 3.11.18 | 20.0-20261102 | `b17d27a` | ✅ 40 passed (pinned packages work on Python 3.11) | – |
| 2026-11-12 | lab | Linux | 3.13 | 20.0-20261102 | `b17d27a` | ✅ 40 passed (3 runs in a row + clean checkout) | – |
| 2026-11-12 | lab | Linux | 3.13 | not running | `b17d27a` | ✅ 21 passed, 19 skipped (offline tests only) | – |

Rows without a report were run before `run_tests.py` existed. **To do:** a full Windows run of the current version (`Application/V3.1`, 41 tests) with `run_tests.py`.

## Before/after (stress tests, scripted AI)
| Test | Before (previous group's V3) | After (V3.1) | Where |
|---|---|---|---|
| 40 parallel requests | 28 failed | 0 failed | Linux |
| 45 abandoned approvals, then a new chat | New chat hung forever | Answered in 0.02 s | Linux |
| Abandoned-approvals test on Windows | – | 203.64 s → **15.05 s** after `localhost` → `127.0.0.1` | Floyd's PC |

## Manual tests with the real AI (Floyd's PC: RTX 3070 Ti, `llama3.1`, Odoo 20.0.20261109)
| Date | Version | Test | Result | Experiment |
|---|---|---|---|---|
| 10 Nov | V3 (original) | "Show me all customers" | ❌ Odoo error (fields sent as text), then the AI **invented customers** | #2 |
| 12 Nov | V3.1 | "Show me all customers" | ✅ Real 17 contacts, text matched (~45 s cold, almost instant warm) | #6, #7 |
| 12 Nov | V3.1 | "Create a sales order for Pepsi with 2 Chair" + approve | ✅ Draft quotation created | #8 |
| 12 Nov | V3.1 | "Create an invoice for Pepsi with 3 Chair" + approve | ✅ Draft invoice; extra field dropped and reported. ⚠️ Approval box text cut off; AI invented "(Untitled)" | #9 |
| 12 Nov | V3.1 | Prices in Odoo of 3 draft invoices | ✅ 150.00 excl. / 181.50 incl. 21% VAT each (also when the AI sent 10.00) | #10 |
| 12 Nov | V3.1 | First message after 10+ min idle with `OLLAMA_KEEP_ALIVE=24h` | ✅ 2–3 s instead of ~40–45 s | #12 |

## Not covered by tests yet
- **AI quality** (does the real model pick the right action and data?): needs the shared test set (Anastasia) and an experiment script (Marija).
- **Chat screen**: no automated frontend tests.
- Full Windows run of the current V3.1 (see "To do" above); other teammates' PCs.
- Odoo Enterprise; multi-company; other taxes/currencies.
