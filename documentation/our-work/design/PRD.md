# Product Requirements Document — AI-Integrated ERP

Version 1.1 · 23 November 2026 · Prepared for the student team and Witek · Readable version: [PRD.html](PRD.html)

Status — Draft for team and supervisor review. This document records the proposed MVP requirements. Implementation status is based on the repository reviewed on 23 November, whose main branch points to commit `33b0168` from 16 November.

## Purpose and problem

Sales and administrative staff spend time navigating ERP screens and entering transaction details. Delayed or incorrect entries reduce the usefulness of business information. The product lets staff describe a transaction in English, review the resolved customer, products, quantities and Odoo prices, and approve creation of a draft record.

Odoo remains the business record system. The intended outcome is faster transaction entry with reliable matching, visible human control and traceable records. The charter's reduction from roughly three minutes to thirty seconds is a target that requires measurement.

## Stakeholders and responsibilities

| Stakeholder | Need | Team or organisation responsibility |
| --- | --- | --- |
| Sales and administrative operators | Simple entry, correct details, understandable errors | Provide guidance, readable approval information and a way to correct requests |
| Companies and managers | Time savings, trustworthy information, reasonable operating cost | Measure results and maintain the ERP configuration and access rights |
| Customers | Correct orders and invoices, appropriate handling of their information | Verify records and correct errors promptly |
| Business partners and suppliers | Accurate information in relevant business processes | Limit the MVP to agreed sales workflows and handle shared information appropriately |
| Project team and supervisor | A bounded, testable deliverable with inspectable evidence | Maintain version control, documentation and evaluation records |
| People responsible for information security and compliance | Controlled access and accountable changes | Use synthetic MVP data, restricted ERP permissions and traceable actions |

The AI agent and Odoo are technical components within these responsibilities. Regulatory requirements should be reviewed by the organisation before use with real transactions.

## MVP scope

The primary flow is natural-language sales ingestion into a draft sales quotation/order. Draft customer invoices and named lookups of customers, products, sales orders and invoices are supported by the current prototype and retained in scope.

The charter requires MCP integration so an external AI assistant can invoke the ERP workflow. The existing React chat is a development and demonstration interface. Clarification of ambiguous names and review are essential workflow steps. A full conversational product, manufacturing, production control, forecasting, payments, posting invoices, confirming sales orders and record deletion sit outside the MVP.

The charter also allows expense logging as an alternative flow. This plan prioritises sales and customer invoicing. Vendor bills require a separate agreed scope change.

## User stories and acceptance criteria

| ID | User story | Acceptance criterion |
| --- | --- | --- |
| R1 | As an operator, I describe a sale in English | The system extracts customer, product and positive quantity without inventing required details. Missing details trigger a question |
| R2 | As an operator, I select the intended customer or product | A unique exact match is used. Otherwise a single partial match is used without asking (for example "Floor" becomes Chair Floor Protection); its effect on precision is part of the evaluation. Multiple matches are offered as a numbered list; the operator replies with the number or the full name. The own company and internal users are never matched as customers. Unknown names produce a clear response. Suggested products require explicit selection |
| R3 | As an operator, I review amounts before approving | Review shows customer, all lines, quantities, Odoo-derived prices, subtotal before tax and relevant warnings. The saved amount agrees with the applicable Odoo pricing configuration |
| R4 | As an operator, I control creation | Approval creates exactly one draft. Rejection or expiry creates none. The system reports the record ID or a clear failure |
| R5 | As an operator, I can work alongside another operator | Two independent sessions can have approvals pending together. Each decision affects its own request. One approval and one rejection create exactly one draft |
| R6 | As a reviewer, I can trace a record | Each created draft has a durable link to its original input, approval decision, timestamp and Odoo ID. Access to that evidence follows the agreed permissions |
| R7 | As an AI-assistant user, I can use ERP tools through MCP | A documented MCP server exposes the agreed actions and completes an end-to-end draft-sales test from an external assistant |
| R8 | As the project team, we can quantify matching performance | A labelled synthetic test set supports precision, recall, confidence-threshold analysis and complete-order accuracy |

## Business and safety rules

1. Odoo supplies prices. The current default is `ODOO_ALLOW_AI_PRICES=false`. User price overrides require a separately agreed design and evaluation.
2. Every creation requires approval and creates a draft. Official confirmation or posting remains a later authorised Odoo action.
3. The backend validates the action, required fields, positive quantities and permitted models. AI output is untrusted input.
4. Current matching uses a unique exact name first, then a unique partial match. Ambiguous results require selection. A product suggestion is restricted to an existing Odoo product and requires selection followed by approval.
5. Possible duplicates produce a warning based on the current same-customer, same-amount, last-24-hours rule. The operator decides whether a repeat transaction is intended.
6. Use synthetic customers, products and transactions for evaluation. Operate through the restricted `ai_agent` ERP account.
7. The assistant does not create new customers. An unknown customer is reported and the operator creates it in Odoo (data-contract decision D5, recommended default).
8. The MVP accepts English input. Dutch is a later extension (D9).
9. Lookups are limited to customers, products, sales orders and customer invoices, with at most 50 rows per answer.

## Evaluation and definition of done

Anastasia prepares the labelled prompts in two parts. The accuracy set holds complete, eligible sales descriptions: 30 first, extended to at least 50. A separate edge-case set holds similar names, typos, unknown entities, missing quantities, price injection attempts and approval/rejection cases. Edge cases do not count towards the 50. Reserve a held-out portion before tuning the matcher and prompts. Record the code commit, model, hardware, data version, expected outcome, actual outcome, timing and evidence for each run.

The charter requires more than 90% correct draft sales orders without edits. For a fixed set of 50 eligible complete sales descriptions, this means at least 46 correct orders. Report clarification and refusal cases separately so their outcomes remain interpretable. Matching precision is correct accepted matches divided by all accepted matches. Recall is correct accepted matches divided by all known-match cases, with deferred cases reported explicitly. Evaluate performance across input quality and threshold settings. Confidence should be based on an evaluated matching method rather than an unsupported model self-rating.

Measure manual Odoo entry and assisted entry using the same transactions. Report cold and warm latency separately and state whether review time is included. Repeat the two-session approval/rejection test and inspect saved Odoo records.

Definition of done, ranked. The ranking is the team's recommendation and must be confirmed against the charter at the review.

- **Must (charter):** the selected flow with draft controls (R1–R5); matching evaluation with the greater-than-90% result (R8); MCP integration in which a person still approves every draft (R7); reviewed PRD, blueprint, schema, setup instructions and demonstration.
- **Should:** traceability (R6). First step: record the conversation ID with every created draft. A durable, restart-proof request store follows.
- **Could, required before real customer data:** authenticated operators and roles.

## Current evidence and remaining work

The repository implements the custom chat/API, draft creation, approval expiry, exact-first matching, ambiguity selection, Odoo price handling, duplicate warnings and JSONL audit events. Anastasia's 16 November browser report verifies five targeted workflow checks on commit `f6bb128`, using scripted AI and real local Odoo. It predates later changes and does not establish real-model accuracy.

## Known risks

- **The real model sometimes picks the wrong action.** On 16 November the same sentence ("sell 4 premium chairs to Luther") became a sales order once and a customer lookup another time (experiment 13). Pull request #8 sets the AI call to temperature 0 and adds a prompt rule. It is not yet verified with the real model. Action choice is the largest risk to the greater-than-90% result.
- **Speed depends on the hardware and on keeping the model loaded.** On the team PC (RTX 3070 Ti, llama3.1, 5.3 GB of GPU memory) a cold model takes about 40–45 seconds for the first answer. With keep-alive the first message after idle takes 2–3 seconds and a warm AI call 0.7–1.0 seconds (experiments 12 and 13). A Mac without a suitable GPU timed out. The thirty-second entry target assumes a warm model; state whether review time is included.

## Remaining acceptance work

MCP integration, evaluated matching confidence thresholds, the greater-than-90% real-model sales result, and a verified durable input-to-record link remain acceptance work. Authenticated operator identity and role/session isolation also require an explicit design and test.

## Ownership and decisions for review

Floyd owns ERP/backend validation and persistence. Marija owns AI extraction and the review interface. Tijn coordinates scope, business rules, test data and supervisor decisions. Anastasia owns test definitions, evidence and documentation. Assign a named MCP owner at the review.

Confirm the MCP workflow, meaning of draft approval versus later posting, matching confidence method, applicable Odoo pricing rules, identity requirements and the supervisor's intended blueprint format.

## Sources

- Project charter supplied to the team, especially deliverables and definition of done.
- Anastasia's stakeholder notes supplied on 23 November.
- [Recorded decisions](../decisions/DECISIONS.md)
- [Test results](../tests/TEST-RESULTS.md)
- [Anastasia's browser QA](../tests/runs/2026-11-16_anastasia-macos-browser-qa.md)
- [Earlier data-contract proposal](data-contract/DATA-CONTRACT.md)
- [Experiment log: real-model measurements](../experiments/EXPERIMENT-LOG.md)
- [System blueprint](BLUEPRINT.md)

## Changes in 1.1

R2 matches the current matching rules; rules 7–9 added; the accuracy set and the edge-case set are separated; known risks added; definition of done ranked (must / should / could); experiment log added as a source.
