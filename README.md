# AI-Integrated-ERP

Project Charter: Minor Data Driven Decision Making
(M3DM)
Project Name: AI-Integrated ERP (“Invisible ERP”)
Project Owners: Witold ten Hove
Project Lead (Student): 
- Anastasios Polymenakos 
- Julian Peters
- Lyndon Boesveld

Start Date: 24-02-2026
End Date: [Date]

Organizational Objective: Traditional ERP systems (like Odoo, SAP) suffer from high friction:
complex UIs with too many fields and menus, constant context switching between
communication tools and ERP, and data latency where transactions are logged days later rather
than real-time. This project aims to eliminate that friction by letting users interact with the ERP
through their existing AI assistants (ChatGPT, Claude, Gemini) using natural language. The
vision: “Chat with your business.”
Data Science Challenge: The core challenge is Entity Resolution — matching unstructured,
natural-language input to structured ERP data. When a sales rep says “I just sold 500 units of
Product X to Acme Corp for $10k”, the system must match “Acme Corp” to the correct partner
record and “Product X” to the correct product, with a measurable confidence score. The project
involves choosing and evaluating matching approaches, analyzing accuracy, and defining
confidence thresholds that balance automation with safety. This adds value for sales reps
(faster data entry), managers (real-time visibility), and contractors (instant expense logging).
Organizational Impact: Primarily operational (reducing time-to-log from ~3 minutes to ~30
seconds per transaction) with tactical implications (improved data quality and real-time
reporting through higher adoption rates).
Data Sources:
ERP master data: Partner records (companies/contacts with name, email, phone) and
Product catalog (name, SKU, internal reference, pricing). An Odoo-compatible schema
definition is provided (see erp-data-schema.md ).
Transaction inputs: Natural language text from AI agents, submitted as structured data
payloads.
Audit trail data: Raw AI prompts stored alongside each draft record for review and
analysis.
All data is generated/synthetic for this MVP — no dependency on external client data.
Data Characteristics: The ERP schema is well-defined. The main data quality challenge is on
the input side: natural language is inherently ambiguous, misspelled, and inconsistent.
1.Project Identification
2. Business Understanding (Objectives & Context)
3. Data Understanding & Scope
05/02/2026, 14:42 project-charter---ai-integrated-erp
localhost:3340 1/3
Analyzing how matching approaches perform across varying input quality is a key part of the
project.
Privacy & Ethics: No real personal data is used in the MVP (synthetic datasets). However, the
design should consider multi-tenant isolation and role-based access. AI-generated entries
should be treated as untrusted input. The draft-first workflow ensures a human always reviews
AI-created records before they become official.
Analytical Techniques: To be determined by the student team. Possible directions include:
String matching / NLP approaches for entity resolution (e.g., fuzzy matching, embeddingbased similarity, or other techniques).
Descriptive analytics to measure match accuracy, false positive/negative rates, and timeto-log improvements.
Process analysis to evaluate the draft-review-confirm workflow and the human-in-theloop experience.
Tooling & Infrastructure: To be determined by the student team. The project requires:
A Model Context Protocol (MCP) server that allows AI assistants to discover and invoke
ERP tools natively.
A database for storing ERP master data and draft transactions.
A method for matching natural language input to structured records.
The existing repository contains a Python-based reference architecture, but students are
free to adapt or replace components based on their own research and preferences.
Analysis/Model:
A working entity resolution component that matches partner names and product references
from natural language input, with measurable precision and recall.
Analysis of matching performance across different input qualities and threshold settings.
Documentation:
A Product Requirements Document (PRD) with user stories and scope definition.
A Technical Design Document (TDD) describing the chosen architecture and technology
stack.
A database schema design for the ERP entities.
Data Product:
A functional MCP server that accepts natural language transaction data from AI assistants
and produces draft ERP records.
At least one working flow: Sales Ingestion (creating draft sale orders) and/or Expense
Logging (creating draft vendor bills).
An audit trail linking each draft record back to the original AI input text.
Definition of Done:
The system can accept a natural language sales description and produce a correct draft
Sale Order with >90% accuracy (no edits needed).
Entity resolution correctly identifies known partners and products above a defined
confidence threshold, and flags uncertain matches for review.
All AI-created records are in draft state and include the original input for traceability.
The MCP server is functional and documented.
4. Methodology & Technology
5. Deliverables & Success Criteria
05/02/2026, 14:42 project-charter---ai-integrated-erp
localhost:3340 2/3
Client Requirements:
Access to the project GitHub repository.
Access to an AI assistant (Claude, ChatGPT, Gemini, or similar) for end-to-end testing.
Team Expectations:
A phased approach is recommended: start with the data model, then build matching logic,
then expose the MCP tools.
All code changes through version control (Git).
Regular communication with the project owner on design decisions, especially around
matching strategies and workflow rules.
Risk Assessment:
Matching accuracy: Natural language is unpredictable. Confidence thresholds may need
tuning, and edge cases (abbreviations, foreign names, typos) require careful handling.
MCP maturity: The Model Context Protocol is relatively new. Documentation and tooling
may evolve during the project.
Scope creep: The project explicitly scopes out two-way AI conversations, manufacturing
flows, and full UI. Staying within MVP scope is critical.
The repository includes example documents for reference. Students are expected to produce their
own versions of these as part of the project:
Product Requirements Document (PRD) — example requirements and user stories
Technical Design Document (TDD) — example architecture and development phases
Model Context Protocol (MCP) — the protocol for AI agent integration (required)
