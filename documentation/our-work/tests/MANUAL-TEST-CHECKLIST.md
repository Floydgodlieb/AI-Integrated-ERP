# Manual test checklist (real AI, V3.1)

For Anastasia (and anyone testing by hand). Run on a PC with a strong enough GPU (Floyd's PC: Marija's Mac timed out with llama3.1).

**Setup:** Odoo 20 with the seed data (`Setup/Quickstart.md`), `Application/V3.1` running, a fresh chat (**+ New Chat**) per test.
There is no shared Odoo: each tester has their own, or restores Floyd's database backup for identical data.

For each test write down: **expected**, **actual**, **seconds**, **pass/fail**. Put the results in [TEST-RESULTS.md](TEST-RESULTS.md) (manual tests table); anything surprising also in the [experiment log](../experiments/EXPERIMENT-LOG.md).

| # | Type in the chat | Expected |
|---|---|---|
| 1 | Create an invoice for Pepsi with 3 Chair → **Approve** | Card: Pepsi, Chair × 3 @ 50.00 = 150.00, total excl. VAT 150.00. In Odoo: draft invoice, 150.00 excl. / 181.50 incl. VAT |
| 2 | Same as 1 again (within 24 h) | Card shows a **"Possible duplicate"** warning; you can still approve or reject |
| 3 | Create a sales order for Pepsi with 2 Desk → **Reject** | "No draft was created"; nothing new in Odoo |
| 4 | … for **pepsi** (lower case) | Resolves to Pepsi (not Pepsi Cola Bottling) |
| 5 | … for **Jansen** | Numbered list (Jansen & Zonen, Jansen Bouw), no card. Reply **2** → card shows Jansen Bouw |
| 6 | … for **Acme**, then reply with the full name **Acme Trading BV** | Card shows Acme Trading BV |
| 7 | … for **Jansen**, then reply **hello** | Treated as a new request; no card |
| 8 | … with 1 **Floor** | Card shows Chair Floor Protection |
| 9 | … for **Globex** | "Could not find …"; no card |
| 10 | … for **My Company** | "Could not find …" (own company is never a customer) |
| 11 | Show me all customers | Table with the 14 seed customers (+ any you created) |
| 12 | **Two users:** two browser windows (or two PCs on a trusted network with `UI_ON_NETWORK=1`), each creating a draft at the same time | Both get their own card and result; nothing mixed up |
| 13 | Start a request, close the browser tab before approving, open a new chat | App still works; nothing was created |
