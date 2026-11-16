# Supervisor check-in – Mon 16 Nov 2026 (Witek)

## Status shown
- Current version: `Application/V3.1` (FastAPI backend + React/Vite UI, local Ollama `llama3.1` → Odoo drafts); V1–V3 archived.
- PR #8 open: temperature 0 + create-vs-lookup rule, and `CLAUDE.md` with build conventions.
- Roughly 75% of the PRD implemented.

## Agreed way of working with Claude
1. Start a project with `/init` so Claude knows the current state.
2. Claude writes three documents: **PRD**, **blueprint/architecture**, **build plan** (phases with subtasks as checkboxes).
3. Every phase ends with a **test gate**; only when the tests pass does Claude commit and push. No broken code on GitHub.
4. Push after every phase; teammates pull the latest before they start.
5. Every change to the PRD or build plan is logged as a decision with the reason ([DECISIONS.md](../../decisions/DECISIONS.md)).
6. Documentation for people is rendered as HTML (Three.js, Motion) so it is readable for humans, not just AI.

## Market testing
- Witek: start user research now instead of waiting until everything is finished (Pareto risk: over-investing in the last 20% before validating the 80% that is built).
- How: find entrepreneurs, show the product, see how they react, collect feedback. LinkedIn outreach is fine next to in-person demos.
- Team would like to improve a bit more first, but agreed it is the logical next step.
- Example from Witek: a business-management intern built a drone-image inventory map for a concrete manufacturer with Claude in a few days; stakeholders reacted very well.

## Next steps
- [ ] Give Witek access to the GitHub repo, so he can follow progress without separate reports.
- [x] Add the HTML / Three.js / Motion rule to the Claude instructions (`CLAUDE.md`).
- [ ] Start entrepreneur outreach: demo to a few entrepreneurs, measure reactions.
- [ ] Next check-in: **Mon 23 Nov 2026**, same time.
