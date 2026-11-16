# Marija Weekly Task

## Done

- The AI now sends one structured action. An invoice action contains the customer name, product names, quantities and optional invoice date. It does not send Odoo IDs or prices. A request to override Odoo's price is set to ask for clarification.
- The backend maps the action to its existing Odoo request. Odoo supplies prices and taxes. A draft is created only after approval.
- Each chat message now makes one AI call. The app writes result and error messages directly, so the AI cannot invent a result after a failed Odoo request.
- Fixed chat streaming so line breaks are kept. Added clearer lookup, create, reject, expiry and connection messages.
- The approval card shows the customer and product lines with quantities, with clear approve and reject buttons. Exact price and tax totals still need to be sent by the backend.
- Added model settings, request timing records and a nine-prompt extraction replay script.
- Updated the local branch to the current `origin/main` base so the V3.1 files are tracked. Nothing was pushed.

## Ollama run

- `llama3.1` is installed. The initial one-prompt pilot took 66.9 seconds and returned an incomplete extraction: it omitted the invoice line and added a date the user did not give.
- The full replay returned an invalid first result in 77.8 seconds, then the second prompt timed out after 120 seconds. The nine-prompt baseline is incomplete on this Mac.
- The pilot output is in `Application/V3.1/results/structured-extraction-20261114-203535.json`.

## Still needed

- Floyd should review the AI fields and finish ambiguous-name handling. The current backend selects the first partial name match.
- The chat approval flow and Odoo price should be checked in the shared Odoo environment. Anastasia's approval, rejection and two-user test is still needed.
- The existing V3 edit was left untouched.
- ESLint is not installed in this workspace, and the automated app tests were not run.
