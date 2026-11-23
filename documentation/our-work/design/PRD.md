
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
| R2 | As an operator, I select the intended customer or product | Unique exact matches are used. Multiple matches are offered for selection. Unknown names produce a clear response. Suggested products require explicit selection |
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

## Evaluation and definition of done

Anastasia prepares 30 labelled prompts first and extends them to 50. Include clear requests, similar names, typos, unknown entities, missing quantities, price injection attempts and approval/rejection cases. Reserve a held-out portion before tuning the matcher and prompts. Record the code commit, model, hardware, data version, expected outcome, actual outcome, timing and evidence for each run.

The charter requires more than 90% correct draft sales orders without edits. For a fixed set of 50 eligible complete sales descriptions, this means at least 46 correct orders. Report clarification and refusal cases separately so their outcomes remain interpretable. Matching precision is correct accepted matches divided by all accepted matches. Recall is correct accepted matches divided by all known-match cases, with deferred cases reported explicitly. Evaluate performance across input quality and threshold settings. Confidence should be based on an evaluated matching method rather than an unsupported model self-rating.

Measure manual Odoo entry and assisted entry using the same transactions. Report cold and warm latency separately and state whether review time is included. Repeat the two-session approval/rejection test and inspect saved Odoo records.

The MVP is complete when the selected flow, matching evaluation, MCP integration, draft controls and durable traceability meet their criteria, and the PRD, blueprint, schema, setup instructions and demonstration are reviewed.

## Current evidence and remaining work

The repository implements the custom chat/API, draft creation, approval expiry, exact-first matching, ambiguity selection, Odoo price handling, duplicate warnings and JSONL audit events. Anastasia's 16 November browser report verifies five targeted workflow checks on commit `f6bb128`, using scripted AI and real local Odoo. It predates later changes and does not establish real-model accuracy.

MCP integration, evaluated matching confidence thresholds, the greater-than-90% real-model sales result, and a verified durable input-to-record link remain acceptance work. Authenticated operator identity and role/session isolation also require an explicit design and test.

## Ownership and decisions for review

Floyd owns ERP/backend validation and persistence. Marija owns AI extraction and the review interface. Tijn coordinates scope, business rules, test data and supervisor decisions. Anastasia owns test definitions, evidence and documentation. Assign a named MCP owner at the review.

Confirm the MCP workflow, meaning of draft approval versus later posting, matching confidence method, applicable Odoo pricing rules, identity requirements and the supervisor's intended blueprint format.

## Proposed marketing extension — campaign attribution for sales

Status — Optional extension for team and supervisor approval. Implementation and field availability need verification.

Sales staff can record the campaign or channel that led to a sale in the same chat request. Marketing staff can then inspect which campaigns are associated with confirmed orders and their order value. This connects marketing activity with the existing sales-entry workflow.

Example input is “Create a sales order for Pepsi with 3 Chair from our Instagram Spring Office campaign.” The approval card shows the customer, products, quantities, Odoo prices, channel and campaign. After approval, the attribution is stored with the draft sales order.

### Users and value

Sales staff record the source while entering the transaction. A marketing coordinator uses the resulting data to compare campaign-associated orders. Managers can identify missing source information and decide where further investigation is needed.

### Requirements and acceptance criteria

| ID | Requirement | Acceptance criterion |
| --- | --- | --- |
| M1 | Capture optional source details | Extract a campaign and channel only when the operator supplies them. A request without source information can continue with attribution marked unknown |
| M2 | Resolve campaign and channel names | Match supplied names to an agreed campaign/channel list. Ask the operator when several entries match or no approved entry exists |
| M3 | Review attribution | Display the resolved campaign and channel before creation. The operator can reject and resubmit a corrected request |
| M4 | Preserve attribution | Save and read back the selected attribution against the created sales order. Verify suitable Odoo fields and backend permissions before implementation |
| M5 | Support a small marketing readout | Provide an agreed Odoo view or export showing confirmed-order count, order value before tax and unknown-source share by campaign for a selected date range |

### Measurement rules

Use synthetic campaigns and sales for the demonstration. Define one operator-reported campaign per order and document the date range and currency used. Report drafts separately from confirmed orders. Confirmed-order value represents orders associated with a campaign. Recognised revenue requires an agreed accounting definition and additional invoice/payment data.

Treat this as operator-reported attribution. It does not establish that a campaign caused a sale. ROI, ROAS and conversion rates require campaign spend or exposure/lead data that the current project does not collect.

### Suggested demonstration and tests

Use two synthetic campaigns, such as Spring Office and Summer Office, and an agreed list of channels. Test an explicit source, an omitted source, an ambiguous campaign, a corrected request and saved attribution after approval. Check that rejection creates no attributed order. Compare a small readout with the underlying confirmed orders.

Anastasia can draft campaign examples, expected outcomes and the marketing readout definition for the team to review. Floyd and Marija should confirm the field mapping, extraction changes and review-card changes. Implement after the core charter acceptance work unless the supervisor agrees a revised priority.

## Sources

- Project charter supplied to the team, especially deliverables and definition of done.
- Anastasia's stakeholder notes supplied on 23 November.
- [Recorded decisions](../decisions/DECISIONS.md)
- [Test results](../tests/TEST-RESULTS.md)
- [Anastasia's browser QA](../tests/runs/2026-11-16_anastasia-macos-browser-qa.md)
- [Earlier data-contract proposal](data-contract/DATA-CONTRACT.md)
- [System blueprint](BLUEPRINT.md)
