# Previous group's documents (archive)

Written by the previous group (Feb–Jun 2026). Moved into topic folders and given clean file names in Nov 2026; **the content is unchanged**. Their code is in `Application/V1`, `V2` and `V3`.

| Folder | File | Original name | Reliability (from our [handover investigation](../our-work/handover/HANDOVER-REPORT.md)) |
|---|---|---|---|
| `product/` | prd.md | PRD.md | Vision and requirements. Many promised features (confidence scores, forecasting, audit trail, rollback) were **never built** |
| `product/` | tdd.md | TDD.md | **Outdated**: describes a CLI, SQL and REST; the real V3 uses a web chat and XML-RPC |
| `product/` | planning.md | planning.md | Early stub |
| `business-processes/` | ontology-order-to-invoice.md | Ontology Order to Invoice .md | **Useful**: roles, allowed/forbidden actions and business rules for order-to-invoice – basis for our validation rules (not wired into their code) |
| `business-processes/` | ontology-procurement-to-pay.md | Ontology Procurement to pay.md | Same for procure-to-pay (not implemented) |
| `technical/` | v1-documentation.md | V1-documentation.md | Explains V1 only |
| `technical/` | installing-odoo.md | Installing-Odoo.md | Their Odoo install notes (Docker); our current setup is in `Setup/` |
| `technical/` | what-model-to-use.md | What-model-to-use.md | Why they chose Ollama + llama3.1 |
| `research/` | debate-20-rounds.md | Debate 20 rounds.md | **AI-simulated** debate between two personas – hypotheses, not evidence |
| `research/` | market-research-without-interviews.docx | Market Research Without Interviews.docx | "Verbatim-style" complaints and percentages **without sources** – treat as hypotheses |
| `research/` | business-plan-and-pricing-strategy.docx | Business Plan and Pricing Strategy.docx | Generic SaaS pricing proposal, 4 references |
| `team/` | ethics.md | Ethics.md | Ethics workshop notes (stakeholders, responsibilities) |
| `team/` | github-guide.md | Github-guide.md | General Git/GitHub introduction |

**Security note:** their code in `Application/V1` and `V2` contains an Odoo password and a Microsoft Teams webhook. Never reuse them; ask the previous group to revoke them.
