# Browser QA results — Anastasia — 16 November 2026

Tested V3.1 at commit `f6bb1284d9e3c5b48ea794d4acc7d541487dddb8` on macOS with two independent Chrome sessions, a running application backend, and an isolated Odoo 20.0-20261116 test database with synthetic data. The project's scripted Ollama stand-in supplied repeatable responses.

| Check | Result | Evidence |
| --- | --- | --- |
| Approval | Pass | Approval created invoice record ID 2. Odoo stored it in draft state. |
| Rejection | Pass | The browser displayed a cancellation message. No invoice was created for the rejected request. |
| Ambiguous customer | Pass | An invoice request for Jansen offered Jansen Bouw and Jansen & Zonen. No approval appeared until a customer was selected. Choosing Jansen & Zonen opened approval for that customer. |
| Odoo pricing | Pass | The scripted AI supplied a unit price of 10.00. Odoo saved 50.00 per chair, for a subtotal of 150.00 before tax for three chairs. |
| Simultaneous browser sessions | Pass | Both Chrome sessions had approval pending before either decision. One approved and the other rejected. The audit log and Odoo database confirmed exactly one new draft for that browser run. |

[Back to the test results index](../TEST-RESULTS.md)
