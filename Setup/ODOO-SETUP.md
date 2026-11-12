# Odoo 20 Community + V3 – reproducible setup

Goal: every team member gets the **same** fresh Odoo with the **same** test customers and products, connected to the V3 app, and can prove it works with one command.

**What was verified and what was not (be aware):**
- ✅ Verified by me on Linux with Docker: Odoo **20.0-20261102** (official `odoo:20.0` image) + **PostgreSQL 17**, `seed_odoo.py` (idempotent, run twice), the limited `ai_agent` user, `check_setup.py`, and the V3 backend creating a draft order and draft invoice as `ai_agent` (with a **scripted stand-in** for the AI model).
- ❓ Not verified by me: the **Windows installer** itself (your build is 20.0.20261109), Ollama and Llama 3.1 on Windows, the real AI model's behaviour. Steps for those follow Odoo's standard behaviour and your screenshots; if a screen looks different, stop and tell whoever guides you.

## 0. Versions to keep identical across the team
| Item | Value |
|---|---|
| Odoo | **20.0 Community** (installer build 20.0.20261109) |
| PostgreSQL | **16 or newer** (the Windows installer bundles its own; Docker route: `postgres:17`). **PostgreSQL 15 does not work with Odoo 20** (tested: error `any_value does not exist`) |
| Database name | `odoo` |
| Apps | **Sales** (`sale_management`) and **Invoicing** (`account`) |
| Demo data | **off** (we load our own test data) |
| Country at DB creation | Netherlands (sets Dutch chart of accounts/taxes, 21% VAT) |
| AI login | `ai_agent` (limited user, created by the seed script) |
| Python | 3.11 or newer (previous group used 3.14; I ran 3.13) |
| Node | 20+ (I used 22) |
| Ollama model | `llama3.1` (what the code hard-codes) |

## 1. Install Odoo (Windows installer) – you did this
1. Run the installer **as administrator**. Type of install: **Odoo Server And PostgreSQL Server** (both boxes ticked).
2. PostgreSQL screen: keep defaults (`localhost`, `5432`, `openpg` / `openpgpwd`). These are the *database's* own login, not your Odoo login. Local machine only; don't expose port 5432.
3. Finish. Odoo runs as a Windows service. Note the **install folder** (e.g. `C:\Program Files\Odoo 20.0.xxxxxxxx`).

## 2. Create the database
1. Open `http://localhost:8069`.
2. Database Manager form:
   - **Master password:** shown on the form, or in `odoo.conf` (key `admin_passwd`) in the install folder under `server`. **Save it** – you need it for backup/restore.
   - **Database name:** `odoo` · **Email:** your email (this is your login) · **Password:** your choice (save it)
   - **Language:** English · **Country:** Netherlands · **Demo data:** unchecked
3. **Create database** (1–2 minutes).

## 3. Install the apps
Apps → install **Sales**, then **Invoicing**. (Community shows "Upgrade"/Enterprise prompts for some features; that's normal.)

## 4. Get the code and tools
Install (all with default options; tick **"Add python.exe to PATH"** for Python): **Git**, **Python 3.11+**, **Node.js LTS**, **Ollama** (ollama.com).
```powershell
git clone https://github.com/Floydgodlieb/AI-Integrated-ERP.git
cd AI-Integrated-ERP
```
The setup files are already in the repo (see §11 for the layout).

## 5. Load the test data and create the limited AI user
The seed script uses only Python's standard library, no install needed. Run from the repo root. PowerShell: **single quotes** around passwords; Command Prompt: **double quotes**.
```powershell
python Setup\seed_odoo.py --db odoo --user you@example.com --password 'YOUR-ODOO-PASSWORD' --create-agent-user --agent-password 'CHOOSE-A-PASSWORD-FOR-THE-AI'
```
Expected: `Customers: created 14` · `Products: created 14` · `Agent user 'ai_agent': created`. Running it again is safe (it says "already there").
Dry run first if you like: add `--check`.

**What you get:** 14 customers incl. confusing pairs on purpose (`Pepsi` / `Pepsi Cola Bottling`, `Jansen Bouw` / `Jansen & Zonen`, `Acme BV` / `Acme Trading BV`, `L. Luther`, `Müller GmbH` …) and 14 products with fixed prices (`Chair` 50.00, `Chair Floor Protection` 12.50, `Ergonomic Chair` 220, `Desk` 200, `Desk Lamp` 25, `Standing Desk` 480, `Keyboard` 35, `Installation Service` 90 …). The full list is at the top of `seed_odoo.py` – edit there, never by hand in Odoo, so everyone stays identical.

**Why a separate `ai_agent` user:** the old code ran as an administrator. `ai_agent` has only *Sales: all documents* and *Invoicing* rights. I tested that it can create draft orders/invoices but is **blocked** from system settings, scheduled jobs and internal tables, and cannot create users **or customers** (so "customer not found" must be handled by a person – decision D5 in the data contract). It can still **read** all customers, orders and invoices, so the backend allow-list is still needed.

## 6. Configure V3
```powershell
copy Application\V3\.env.example Application\V3\.env
notepad Application\V3\.env
```
Set:
```
ODOO_URL=http://127.0.0.1:8069
ODOO_DB=odoo
ODOO_USER=ai_agent
ODOO_PASS=THE-AI-PASSWORD-FROM-STEP-5
TEAMS_WEBHOOK_URL=
```
Leave `TEAMS_WEBHOOK_URL` empty (the old webhook was leaked; never use it). **`.env` is git-ignored – never commit it.**

## 7. Install and start V3
```powershell
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r Application\V3\backend\requirements.txt
cd Application\V3\chat-UI
npm install
cd ..
python main.py
```
`main.py` (Windows launcher from the previous group) starts the backend on **:8001** and the chat UI on **:5173**; it expects the virtual environment in `.venv` at the repo root, exactly as created above. Stop with Ctrl+C. (Using `.venv\Scripts\python.exe` directly avoids PowerShell's "running scripts is disabled" error.)

## 8. Ollama and the model
```powershell
ollama pull llama3.1
ollama run llama3.1 "Say hello in five words"
```
(~4.7 GB download.) Note how many **seconds** the first answer takes: write it in the table in §10 – it is your first latency baseline. Later, `OLLAMA_KEEP_ALIVE=-1` keeps the model loaded.

## 9. Verify everything with one command
```powershell
python Setup\check_setup.py --env-file Application\V3\.env
```
Expected: all `[ OK ]` (Odoo version, login as `ai_agent`, apps, 14 customers, 14 products, "cannot read system settings", Ollama + model, backend health). Read-only; changes nothing. `[WARN]` for the backend just means it isn't running.

**Test transaction (in the browser, `http://localhost:5173`):**
1. "Show me all customers" → a table with your 14 customers.
2. "Create a sales order for Pepsi with 2 Chair" → approval dialog → ✓ → in Odoo: **Sales → Orders → Quotations** shows a **draft** quotation for Pepsi.
3. "Create an invoice for Pepsi with 3 Chair" → approve → Odoo **Invoicing → Customers → Invoices** shows a **draft** invoice.
4. Known behaviour of V3 (see handover report): the price the AI gives is trusted, matching is fuzzy, creating a *new customer* will fail for `ai_agent`. These are what the next sprints fix. The real Llama 3.1 may format things differently than my scripted tests – note anything odd in the experiment log.

## 10. Record what you actually used (fill in – this is your reproducibility proof)
| Item | Value | Date | Who |
|---|---|---|---|
| Odoo build (installer title) | 20.0.20261109 | | |
| Odoo version (`check_setup.py` output) | | | |
| PostgreSQL version | | | |
| DB name / apps installed | `odoo` / Sales, Invoicing | | |
| Seed script version (git commit) | | | |
| Python / Node versions | | | |
| Ollama version / model tag | | | |
| First `ollama run` answer time (s) | | | |
| `check_setup.py` result | | | |

## 11. Where the setup files are in the repo
```
Setup/
  ODOO-SETUP.md          (this file)
  seed_odoo.py           (test data + ai_agent user; idempotent)
  check_setup.py         (read-only verification)
  docker-compose.yml     (Docker alternative: Odoo 20 + PostgreSQL 17)
documentation/data-contract/
  DATA-CONTRACT.md  schemas_draft.py  contract_examples.json  test_contract.py
```

## 12. Share the exact same database with the team (fastest way to be identical)
After steps 1–5 are done once, one person makes a backup: `http://localhost:8069/web/database/manager` → **Backup** (format **zip**, includes files; needs the master password). Share the zip via your team drive (**not** Git: it contains user data and password hashes). Teammates install the same Odoo 20.0 and use the same page → **Restore**. Same major version required.
**Start over / reset test data:** Database Manager → **Delete**, create it again (§2–3), run the seed (§5), or **Restore** your backup.

## 13. Troubleshooting
| Symptom | Fix |
|---|---|
| `http://localhost:8069` doesn't load | Services → "odoo-server-20.0…" → Start; check nothing else uses port 8069 |
| "Login failed" in `seed_odoo.py` | `--user` is the **email** you typed in the DB form; `--db` must match the DB name exactly |
| `python` not found | Reinstall Python with "Add to PATH", or try `py` instead of `python` |
| PowerShell: "running scripts is disabled" | Don't activate the venv; use `.venv\Scripts\python.exe -m …` as in §7 |
| UI says "Odoo not connected" | `.env` wrong or Odoo down; run `check_setup.py` |
| Creating a new customer via chat fails | Expected: `ai_agent` cannot create customers (by design); create it in Odoo |
| Windows Firewall prompt | Allow on **private** networks |
| Everyone's data differs | Don't edit data by hand; change `seed_odoo.py` and re-run, or restore the shared backup |

## 14. Docker route (Mac / Linux, or Windows with Docker Desktop) – tested on Linux
```bash
docker compose -f Setup/docker-compose.yml up -d
# one-off: create the database with Sales + Invoicing, no demo data
docker compose -f Setup/docker-compose.yml run --rm odoo odoo -d odoo -i sale_management,account --without-demo=True --stop-after-init
python Setup/seed_odoo.py --db odoo --user admin --password admin --create-agent-user --agent-password 'CHOOSE-ONE'
```
Odoo at `http://localhost:8069`; the CLI-created database has login **admin / admin** (change it if the machine is shared). Wipe everything: `docker compose -f Setup/docker-compose.yml down -v`. Note: I ran this once with the old `--without-demo=all`, which Odoo 19+ reports as invalid and treats as True (warning). `=True` is the correct form; I did not re-run with it.
