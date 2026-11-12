# Documentation

Two parts: **`previous-group/`** is what the previous group left us (archive, content untouched). **`our-work/`** is everything from our group.

## Start here
| You want to … | Read |
|---|---|
| Set up the project on your PC | [`Setup/Quickstart.md`](../Setup/Quickstart.md) (in the repo root) |
| Understand what the previous group built | [HANDOVER-REPORT.md](our-work/handover/HANDOVER-REPORT.md) |
| See everything we changed | [CHANGELOG.md](our-work/changes/CHANGELOG.md) |
| See test results | [TEST-RESULTS.md](our-work/tests/TEST-RESULTS.md) |
| See measurements and what we learned | [EXPERIMENT-LOG.md](our-work/experiments/EXPERIMENT-LOG.md) |
| Know who does what | [roles-and-tasks.pdf](our-work/planning/roles-and-tasks.pdf) |
| Start on the AI & chat side (Marija) | [HANDOFF-MARIJA.md](our-work/planning/HANDOFF-MARIJA.md) |

## our-work/
| Folder | Contents |
|---|---|
| [`handover/`](our-work/handover/) | [HANDOVER-REPORT.md](our-work/handover/HANDOVER-REPORT.md) – full investigation of the previous group's work (snapshot 9–10 Nov 2026) · [SESSION-OVERVIEW.md](our-work/handover/SESSION-OVERVIEW.md) – first setup session (snapshot 10 Nov) |
| [`planning/`](our-work/planning/) | [TEAM-PLAN.md](our-work/planning/TEAM-PLAN.md) – workstreams, timeline, backlog · [roles-and-tasks.pdf](our-work/planning/roles-and-tasks.pdf) – roles and tasks per person · [project-overview.pdf](our-work/planning/project-overview.pdf) – 2-page visual summary · [HANDOFF-MARIJA.md](our-work/planning/HANDOFF-MARIJA.md) |
| [`changes/`](our-work/changes/) | [CHANGELOG.md](our-work/changes/CHANGELOG.md) – all changes per pull request, plus V3 vs V3.1 at a glance · [BACKEND-CHANGES.md](our-work/changes/BACKEND-CHANGES.md) – technical detail of the backend work |
| [`tests/`](our-work/tests/) | [TEST-RESULTS.md](our-work/tests/TEST-RESULTS.md) – automated runs, before/after, real-AI tests · [`runs/`](our-work/tests/runs/) – full report of each test run |
| [`experiments/`](our-work/experiments/) | [EXPERIMENT-LOG.md](our-work/experiments/EXPERIMENT-LOG.md) – hypothesis → change → measurement → lesson (grading evidence) |
| [`design/`](our-work/design/) | [`data-contract/`](our-work/design/data-contract/) – DRAFT of what the AI may send to the backend (to agree between Floyd and Marija) |
| [`decisions/`](our-work/decisions/) | [DECISIONS.md](our-work/decisions/DECISIONS.md) – what we decided and why; open decisions |

## previous-group/
Archive of the previous group's documents, renamed to clean file names but **content unchanged**. Read [previous-group/README.md](previous-group/README.md) first: it says which documents are reliable and which are outdated or unsourced.

## Rules for adding documentation
- New documents go in `our-work/`, in the folder that fits; nothing new in `previous-group/`.
- File names: no spaces. Our documents: `UPPERCASE-WITH-DASHES.md`.
- Every pull request adds an entry to [CHANGELOG.md](our-work/changes/CHANGELOG.md).
- Every experiment gets an entry in [EXPERIMENT-LOG.md](our-work/experiments/EXPERIMENT-LOG.md); every test run a row in [TEST-RESULTS.md](our-work/tests/TEST-RESULTS.md) (`Setup/run_tests.py` writes the report).
- Old documents that are no longer current: add a dated "snapshot" note at the top instead of deleting them.
