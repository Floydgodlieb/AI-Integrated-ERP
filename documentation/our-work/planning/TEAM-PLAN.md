> **Snapshot – 9 Nov 2026.** Work plan by workstream. Roles and names were assigned later: see [roles-and-tasks.pdf](roles-and-tasks.pdf). Stages 0–6, 9 and 10 of workstream 1 are done (see [CHANGELOG](../changes/CHANGELOG.md)).

# Project Plan – AI-Integrated ERP (work only, no roles assigned yet)

*Based on the handover report. Nobody is assigned to anything in this version. The work is grouped into workstreams so you can assign it later. The final presentation date is unknown to me, so later phases are counted backwards from it (see §4).*

**Direction (from the report, Part 9):** a **trustworthy AI invoicing slice** (validation, human approval, audit) on top of V3, plus a **latency and model benchmark** workstream. Stretch idea only if ahead of schedule: local document-to-invoice.

**Goal in one sentence:** *a chat that turns "invoice Pepsi for 3 chairs" into a correct, validated, human-approved draft invoice in Odoo, fast, with measured accuracy and measured speed.*

---

## 1. Workstreams (unassigned)

| Workstream | Needs code? | What it covers |
|---|---|---|
| **1. Backend & Odoo integration** | Yes | Stability, security hygiene, validation, invoice logic, audit log, Docker |
| **2. AI, latency & frontend** | Yes | Structured output, prompts, speed, model comparison, evaluation runner, approval screen |
| **3. Product, project & Odoo/finance domain** | No | Scope, backlog, supervisor sessions, previous group, Odoo business setup, business rules, demo story |
| **4. Quality, research & documentation** | No | Test set, manual testing, experiment log, research checks, docs, slides, backup video |

**Handoffs between workstreams** (who does them is up to you):
- Workstream 3 → 1 and 2: business rules, Odoo master data, acceptance criteria.
- Workstream 4 → 2: the test dataset the evaluation runner replays.
- Workstream 1 → 2: stable actions and API to build the AI and UI on.
- Workstreams 2 → 3 and 4: measurements (accuracy, seconds per request) for sprint reports.
- Workstreams 3 and 4 together: demo script, backup video and presentation.

---

## 2. What each workstream contains

### Workstream 1 – Backend & Odoo integration
| Area | Tasks (from the report's findings) |
|---|---|
| Security & hygiene | Revoke leaked Odoo password and Teams webhook; remove `__pycache__` from Git; secret scanning; remove V1/V2 from `main` |
| Stability | Fix the shared, non-thread-safe Odoo connection; add timeouts and retries; make the Teams post async with a timeout |
| Approval flow | Replace the blocking wait with a pending-action store that expires; the confirm endpoint must match the session |
| Architecture | An action registry (name, JSON schema, resolver, validator, executor, summariser) so invoicing is one action instead of special cases in four places |
| Validation | Exact/ranked name matching and "did you mean…?" on ambiguity; price and tax from Odoo's pricelist; quantity/date checks; duplicate/idempotency check; allow-list of Odoo models and fields |
| Order-to-cash | Link invoice to sales order; separate **confirm** and **post** actions; draft by default |
| Audit | Append-only action log (what, input text, approved by, Odoo ID) |
| DevOps | `docker-compose` for Odoo + Postgres (Ollama optional); cross-platform start script; pinned `requirements.txt`; a DB reset/seed script |
| Odoo version risk | Thin adapter around XML-RPC so JSON-2 can be swapped in |

**Output:** passing tests, compose file, one-page architecture note.

### Workstream 2 – AI, latency & frontend
| Area | Tasks |
|---|---|
| Structured output | Ollama JSON-schema `format` for invoice extraction (customer, lines, date), validated with Pydantic before touching Odoo |
| Prompting | Slimmer system prompt; few-shot examples from the test dataset; stop sending raw search results back to the model |
| Latency | Timing instrumentation (per LLM call, per Odoo call, end to end); `keep_alive`; one LLM call per turn; history trimming; `num_ctx` tuning; cache customer/product lists |
| Model benchmark | Compare `llama3.1` against 2–3 newer tool-capable models: accuracy, wrong-ID rate, seconds per request |
| Evaluation runner | Script that replays the test prompts against a clean Odoo DB, compares with expected results and outputs a report |
| Frontend | Fix SSE parsing (multi-line `data:`), ESLint errors, placeholder text; an approval card (all lines, totals, tax, warnings, "ambiguous – choose one"); loading/expiry/error states |
| Demo reliability | Model pre-warm script; deterministic demo dataset loader |

**Output:** evaluation runner, baseline and after-optimisation reports, new approval UI.

### Workstream 3 – Product, project & Odoo/finance domain
| Area | Tasks |
|---|---|
| Project management | Board and issues (§5); weekly sprint prep and the 30-min supervisor session (progress / plan / blockers); decision log |
| Previous group | Send the email first (questions in report §10.2): Odoo version/modules, DB dump or seed script, unpushed work, hardware and timings, licence/permission; chase replies; get their videos |
| Odoo functional setup | Install Odoo (report Part 7); create realistic master data: ~20 customers (incl. near-duplicates like "Pepsi" / "Pepsi Cola Bottling"), ~30 products with prices/taxes, a price list, payment terms |
| Ask AI check | 1–2 h hands-on test of Odoo's Ask AI (verify edition availability); one-page finding: what it can and can't do, what we must not claim |
| Business rules | Turn `documentation/previous-group/business-processes/ontology-order-to-invoice.md` into numbered, testable rules with allowed / blocked / ask-user outcomes |
| Acceptance criteria | Given/when/then statements per user story |
| Demo | Demo storyline with 3 scenarios (happy path, ambiguous customer, blocked/hallucinated request) and a rehearsal schedule |
| Commercial angle | Short, honest value hypothesis (who pays, what pain) |

**Output:** board, weekly sprint notes, `docs/rules.md`, Odoo seed data spec, demo storyline.

### Workstream 4 – Quality, research & documentation
| Area | Tasks |
|---|---|
| Evaluation dataset | 50 test prompts in a spreadsheet: input text, expected customer/product/qty/price, expected outcome (create / ask-user / reject), category (clean, typos, ambiguous, missing info, hallucinated customer, duplicate, injection attempt, wrong price); exported as CSV/JSON |
| Manual QA | Run the app by hand each sprint against the dataset and acceptance criteria; bug reports with reproduction steps; pass-rate per sprint |
| Experiment / learning log | Hypothesis → change → measurement → result → what we learned (this is your grading evidence) |
| Research | Verify the unverified claims in report Part 8 before quoting; keep a source list; 2-page landscape summary |
| Security/ethics | Short privacy and ethics note (local model keeps data on-prem; approvals; audit log); update `previous-group/team/ethics.md` |
| Documentation | Update `README.md` (setup, architecture, how to run the evaluation); keep `docs/` tidy |
| Presentation | Slide deck; backup demo video (recorded early, re-recorded after freeze); rehearsal timekeeping |
| Commercial angle | Market/pricing sanity check; treat the existing docx files as hypotheses only (they are unsourced) |

**Output:** `eval/dataset.csv`, experiment log, pass-rate chart, docs, deck, video.

---

## 3. Working agreements (draft, adapt freely)

- **Git:** `main` is protected; every change goes through a pull request with a review from someone other than the author. Branch names `feat/…`, `fix/…`, `docs/…`.
- **Never commit:** `.env`, passwords, webhook URLs, `__pycache__`.
- **Rituals:** short stand-up twice a week (or async post); weekly planning the day before the supervisor session; 30-min supervisor session; retro after every second sprint.
- **Definition of Done:** merged via reviewed PR, tests pass, relevant test cases re-run, docs/README updated, experiment-log entry written.
- **Decisions:** one line in the decision log (what / why / alternatives).
- **Pairing suggestion:** pair on the two risky handoffs: business rules → validators, and test dataset → evaluation runner. Most misunderstandings happen there.

---

## 4. Timeline

Weeks count from your start in **week 7**. Fill in real dates once the final presentation date is known. The **freeze is 2 weeks before the presentation** (supervisor rule).

### Pre-week-7 (your supervisor's preparation list)
| # | Task | Workstream | Done when |
|---|---|---|---|
| P1 | Email previous group (repo, DB dump, hardware/timings, licence, questions) | 3 | Sent; replies tracked |
| P2 | Watch previous group's videos; write a 1-page "what they showed" | 4 | Notes in `docs/` |
| P3 | Everyone reads report TL;DR + Parts 1, 3, 4 | all | Anyone can explain the flow in 3 minutes |
| P4 | **Team meeting 1:** run report Part 7 setup together on every laptop; everyone records seconds for one reply (latency baseline) | 1 hosts, all join | Baseline table filled in |
| P5 | Revoke leaked credentials; remove secrets from files | 1 | Confirmed revoked |
| P6 | Ask AI hands-on check + findings page | 3 | Page written |
| P7 | Verify the Part 8 claims you will quote | 4 | Source list with ✔/✘ |
| P8 | Create board and issues (§5); repo hygiene (`.gitignore`, branch protection) | 3 and 1 | Board live |
| P9 | **Team meeting 2:** confirm direction, split of work, demo scenario, definition of done | all | Decisions logged |

### Sprint 1 (week 7) – "Safe and measurable foundation"
- **Workstream 1:** concurrency fix, approval store with expiry, remove secrets/pycache/V1–V2, compose file for Odoo + Postgres, first 5 tests.
- **Workstream 2:** timing instrumentation, baseline latency on every laptop, SSE parsing fix, ESLint fix, evaluation-runner skeleton.
- **Workstream 3:** previous-group follow-up; Odoo master data spec and seeded DB; rules spec v1 (about 10 rules); sprint plan and supervisor session.
- **Workstream 4:** dataset v1 (30 prompts) and scoring rules; manual run of current V3 for a baseline pass-rate; experiment log set up.
- **Show the supervisor:** baseline numbers (X% correct, Y seconds per request) and what was fixed.

### Sprint 2 (week 8) – "Invoice pipeline v1"
- **Workstream 1:** action registry; invoice action with validators; ranked name matching and ambiguity response; price/tax from Odoo's pricelist.
- **Workstream 2:** structured output for invoice extraction; slimmer prompt; one-LLM-call flow; evaluation runner produces a report.
- **Workstream 3:** rules spec v2 and acceptance criteria; DB reset tested; start demo storyline.
- **Workstream 4:** dataset v2 (50 prompts incl. ambiguous/hallucinated/injection); run evaluation; log before/after.
- **Show the supervisor:** old flow vs new, with accuracy and latency numbers.

### Sprints 3–4 – "Complete the order-to-cash slice"
- Link invoice to sales order; separate confirm/post actions; idempotency/duplicate detection; audit log; JSON-2 adapter spike.
- Model benchmark (3 models); `keep_alive` / `num_ctx` / history trimming; approval card with warnings and "choose one".
- Acceptance walkthroughs with supervisor feedback; finalise 3 demo scenarios; commercial hypothesis.
- Regression run every sprint, bug reports, pass-rate chart, research summary, ethics note.

### Sprints 5+ – "Harden and decide"
- Fix top defects from the regression results; decide on the stretch (document → invoice **feasibility spike only**) or hardening.
- Agree a performance target with the supervisor (e.g. "end to end under N seconds on the demo laptop"); stop adding features.

### Freeze (2 weeks before the presentation)
- No new features, only bug fixes everyone agrees on.
- Tag a release; run the README setup on a clean machine; tune the demo laptop and pre-warm the model; finalise storyline and deck; **record the backup video**.

### Last two weeks – presentation prep (everyone)
- 3 full timed rehearsals with the live demo, one using the backup video to confirm it is usable.
- Q&A prep: honest limitations, next steps, commercial angle, lessons from the experiment log.

---

## 5. Starter backlog (copy into GitHub Issues)

| ID | Title | Workstream | Size | Sprint |
|---|---|---|---|---|
| T1 | Revoke leaked credentials; purge secrets/pycache; add secret scanning | 1 | S | 1 |
| T2 | Thread-safe Odoo client (pool/lock), timeouts, retries | 1 | M | 1 |
| T3 | Pending-action store + approval expiry (no blocking threads) | 1 | M | 1 |
| T4 | Docker compose for Odoo + Postgres; DB reset/seed script | 1 (+3 for data) | M | 1–2 |
| T5 | Action registry + invoice action skeleton | 1 | L | 2 |
| T6 | Validators: ambiguity, pricelist price/tax, qty/date, duplicate check, model/field allow-list | 1 (+3 for rules) | L | 2–3 |
| T7 | Link invoice ↔ sales order; separate confirm/post actions | 1 | M | 3 |
| T8 | Audit log table + view | 1 | M | 3 |
| T9 | Timing instrumentation + latency baseline per laptop | 2 | S | 1 |
| T10 | SSE parsing fix, ESLint errors, remove placeholders | 2 | S | 1 |
| T11 | Structured output (JSON schema) + Pydantic validation for invoice extraction | 2 | M | 2 |
| T12 | One-LLM-call flow, slimmer prompt, history trimming, `keep_alive` | 2 | M | 2–3 |
| T13 | Evaluation runner (dataset → run → score → report) | 2 | L | 1–2 |
| T14 | Model benchmark report (3 models) | 2 | M | 3–4 |
| T15 | Approval card UI (lines, totals, warnings, choose-one) | 2 | M | 3 |
| T16 | Email previous group; track replies; summarise their videos | 3 and 4 | S | pre-7 |
| T17 | Odoo master data spec (customers incl. near-duplicates, products, price list, terms) | 3 | M | 1 |
| T18 | Rules spec v1/v2 from the ontology (numbered, testable) | 3 | M | 1–2 |
| T19 | Ask AI hands-on findings | 3 | S | pre-7 |
| T20 | Acceptance criteria + demo storyline (3 scenarios) | 3 | M | 2–4 |
| T21 | Sprint board, weekly agenda, decision log | 3 | S | 1 |
| T22 | Dataset v1 (30) → v2 (50 prompts) with expected outcomes | 4 | M | 1–2 |
| T23 | Manual regression each sprint + bug reports + pass-rate chart | 4 | M | 1+ |
| T24 | Experiment / learning log | 4 | S | 1+ |
| T25 | Verify Part 8 claims; research summary; ethics note | 4 | M | pre-7–3 |
| T26 | README/docs update; setup guide check on a clean machine | 4 (+1) | M | 2–4 |
| T27 | Slide deck + backup video | 4 (+3) | L | 5+ |
| T28 | Stretch: document → invoice feasibility spike | 2 (+1) | L | 5 |

Sizes: S ≤ ½ day · M ≈ 1–2 days · L ≈ 3–5 days.

---

## 6. Risks to the plan

| Risk | Handling |
|---|---|
| Code work becomes the bottleneck | Rules, data, test set, research and docs run in parallel from week 7 |
| Non-code members feel disconnected from the code | Pairing sessions on handoffs; run the app and the evaluation every sprint; everyone attends the demos |
| Work piles up on one person | Clear file/area ownership once you assign; cross-review of PRs; "who is blocked?" in every stand-up |
| Scope creep | Anything not in the backlog needs team agreement; stretch only after Sprint 4 targets are met |
| Laptop too slow for the model | Baseline in P4; benchmark smaller models; agree demo hardware early |
| Knowledge held by one person | Every PR needs a reviewer; keep decisions and docs current |
| Previous group doesn't answer | Chase twice, then ask the supervisor; plan assumes only what is in the repo |
