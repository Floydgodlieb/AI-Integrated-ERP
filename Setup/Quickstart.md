# Quickstart: run the previous group's V3 on your own Windows PC

**What you get:** the AI chat (V3, exactly as the previous group left it) talking to your own local Odoo 20 with 14 test customers and 14 test products. **No code changes needed.** Takes about 45 minutes, most of it downloading.

> This guide was followed step by step on a real Windows 10 PC. Everything is typed into **Command Prompt** (press the Windows key, type `cmd`, press Enter). Not PowerShell.

---

## A. Install five programs (default options everywhere)

| # | Program | Where | Check it worked (in Command Prompt) |
|---|---|---|---|
| 1 | **Python 3.11 or newer** (tick "Add python.exe to PATH") | python.org/downloads | `python --version` |
| 2 | **Git** | git-scm.com | `git --version` |
| 3 | **Node.js (LTS)** | nodejs.org | `node --version` |
| 4 | **Ollama** (runs the AI) | ollama.com/download | open a **new** Command Prompt, `ollama --version` |
| 5 | **Odoo 20 Community, Windows installer** | odoo.com/download | see step B |

We used: Python 3.12.10, Git 2.56, Node 26.12, Ollama 0.40.16, Odoo 20.0.20261109. Newer is normally fine.

## B. Install Odoo and create the database

1. Run the Odoo installer **as administrator**. Choose **"Odoo Server And PostgreSQL Server"** (both boxes ticked). Keep every default (the PostgreSQL screen shows `localhost`, `5432`, `openpg`, `openpgpwd`: leave it). Finish.
2. Open **http://localhost:8069** in your browser. Fill in the database form:

   | Field | Enter |
   |---|---|
   | Master Password | leave the generated one. **Copy it somewhere safe** |
   | Database Name | `odoo` (exactly) |
   | Email | your email (this is your Odoo login) |
   | Password | your choice. **Write it down** |
   | Phone | empty |
   | Language / Country | English (US) / Netherlands |
   | Demo Data | **unchecked** |

   Click **Create database** and wait 1–2 minutes (don't refresh).
3. Open **Apps** (grid icon top-left, or http://localhost:8069/odoo/apps). Click **Activate** on **Sales**, wait, then on **Invoicing** (it may already be done). Don't activate other apps.

## C. Get the code and the setup files

```
cd %USERPROFILE%\Documents
git clone https://github.com/Floydgodlieb/AI-Integrated-ERP.git
cd AI-Integrated-ERP
```
Then extract **Teammate-Setup-Kit.zip** (from Floyd) **into this folder** (right-click → Extract All → choose the `AI-Integrated-ERP` folder). Check:
```
dir setup
```
You should see `seed_odoo.py` and `check_setup.py`. *(If the kit is already in the repo after a `git pull`, skip the zip.)*

## D. Fill Odoo with the test data

Replace the email/passwords. Choose a new password for the AI user: **only letters, digits and hyphens**. Write it down.
```
python setup\seed_odoo.py --db odoo --user YOUR-ODOO-EMAIL --password "YOUR-ODOO-PASSWORD" --create-agent-user --agent-password "CHOOSE-AI-PASSWORD"
```
Expected last lines:
```
Customers: created 14, already there 0
Products : created 14, already there 0
Agent user 'ai_agent': created
```
Safe to run again (it never creates duplicates). Add `--check` to only look.

## E. Tell V3 how to reach Odoo

```
copy Application\V3\.env.example Application\V3\.env
notepad Application\V3\.env
```
Make the file exactly this (use the **AI password** from step D) and save:
```
ODOO_URL=http://localhost:8069
ODOO_DB=odoo
ODOO_USER=ai_agent
ODOO_PASS=YOUR-AI-PASSWORD
TEAMS_WEBHOOK_URL=
```
**Leave the last line empty.** (The template contains a fake address that can freeze the app.) Never commit `.env`.

## F. Install V3

```
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r Application\V3\backend\requirements.txt
cd Application\V3\chat-UI
npm install
cd ..\..\..
```
"vulnerabilities" warnings from `npm` and the "upgrade pip" notice: ignore.

## G. Download the AI model (about 5 GB)

In a **new** Command Prompt:
```
ollama pull llama3.1
ollama run llama3.1 "Say hello in five words"
```
Time it with a stopwatch. **The first run is slow** (it loads the model: ~40 s on our PC). Run it again: it should take about a second. Type `/bye` to leave.

## H. Check everything

```
cd %USERPROFILE%\Documents\AI-Integrated-ERP
python setup\check_setup.py --env-file Application\V3\.env
```
All lines should be `[ OK ]` (the "V3 backend not running" line is only a warning until step I).

## I. Start the app

```
cd %USERPROFILE%\Documents\AI-Integrated-ERP\Application\V3
..\..\.venv\Scripts\python.exe main.py
```
Allow Windows Firewall for **private** networks if asked. Open **http://localhost:5173**. Stop with **Ctrl+C**.

---

## What to expect (important: this is the previous group's unchanged code)

Try these in the chat, then **check the answers in Odoo** (Sales → Orders → Customers / Quotations; Invoicing → Customers → Invoices):

1. `Show me all customers`
2. `Create a sales order for Pepsi with 2 Chair` → approval dialog → ✓ → a **draft** quotation appears in Odoo
3. `Create an invoice for Pepsi with 3 Chair` → approve → a **draft** invoice appears

**Known problems of the old version. They are not your fault:**
- **The AI can make things up.** On our PC, "Show me all customers" failed and the AI then invented customers (John Doe, Jane Smith…) that do not exist. **Always compare with Odoo.** (We have a tested fix, not applied yet.)
- If the app shows a grey **"Executed"** bubble instead of a table, the request failed.
- Line breaks in answers are lost.
- The first request after a few minutes of idle is slow (the model unloads).
- Only **draft** orders and invoices are created. Creating a **new customer** through the chat fails by design (the AI user may not).
- `main.py` opens the chat to your whole Wi-Fi (`Network:` line). Don't run it on shared or university Wi-Fi.
- Everyone's AI answers can differ from run to run.

## If something goes wrong

| Problem | Fix |
|---|---|
| `python` / `ollama` "not recognized" | Close Command Prompt, open a **new** one. Still no? Reinstall (Python: tick "Add to PATH") |
| http://localhost:8069 doesn't load | Press Windows key → `services` → start **odoo-server-20.0…**; wait a minute |
| `Login failed` in the seed script | `--user` is the **email** from the database form; database must be called `odoo` |
| Chat says "Odoo not connected" | `.env` wrong (user `ai_agent`, the **AI** password) → run `check_setup.py` |
| `localhost:8001/api/health` is not `{"status":"ok"}` | Same: check `.env` |
| `ollama pull` is stuck | Check disk space (needs ~6 GB) and internet |
| Everyone's data looks different | Never type data by hand; re-run the seed script, or use the fast lane below |

## Fast lane: identical Odoo for everyone (skip steps B2, B3, D)
One person finishes B–D once, then in the browser: **http://localhost:8069/web/database/manager → Backup** (zip, with the master password) and shares the zip on the team drive (**not** on GitHub). The others install Odoo (B1), open the same page → **Restore**. Same Odoo 20 required.

## Send this back to the team (copy into the shared record)

| Item | Your value |
|---|---|
| CPU / RAM / graphics card | |
| Odoo version (from `check_setup.py`) | |
| Ollama version / model | |
| `ollama run` first answer (seconds) | |
| `ollama run` second answer (seconds) | |
| `check_setup.py` result | |
| First chat test ("Show me all customers"): table, error, or invented names? | |
