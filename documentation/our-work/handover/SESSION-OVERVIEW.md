> **Snapshot – 10 Nov 2026.** What was done in the first handover session; several open items listed here have been done since (backend hardening, V3.1, experiment log). For the current state see [CHANGELOG](../changes/CHANGELOG.md), [test results](../tests/TEST-RESULTS.md) and the [experiment log](../experiments/EXPERIMENT-LOG.md).

# Overview: everything we did (session of 9–10 Nov 2026)

*Facts only. Every ✅ below was actually run or checked. ⚠️ means a limit or something still open.*

## 1. In one paragraph
We took over the previous group's AI-ERP project (a local AI chat, **V3**, that reads and creates records in **Odoo**). I investigated the repository and documentation, ran the code against a real Odoo, found its main weaknesses, researched the market, and wrote a plan with roles. Then you set up the whole thing on your own Windows PC: Odoo 20 Community, test data, the V3 app and the AI model. The first real chat test **failed in an instructive way**: the AI invented customers. I diagnosed the exact cause and built a tested fix, but **nothing has been applied to your code yet**.

## 2. Timeline

| # | What | Result |
|---|---|---|
| 1 | **Investigation** of the repo (V1 → V2 → V3), 43 commits (24 Feb–12 Jun 2026), the 13 documentation files and both Word documents | V3 is current. V3 is small: ~600 lines of Python (agent 335, API 119, Odoo client 104, launcher 43) plus a chat UI; all three versions together are ~1,100 lines of Python. Most ambitions in the PRD (forecasting, confidence scores, audit trail, rollback) are **not in the code** |
| 2 | **Ran V3 against a real Odoo 19** (Docker) with a scripted stand-in for the AI ⚠️ (Ollama download was blocked in my sandbox) | Works: login, read, create **draft** order/invoice after approval, decline, invented-customer rejection. Broken: see §4 |
| 3 | **Research** on Odoo AI, competitors, local models (a helper agent; vendor claims are partly unverified) | Odoo's Ask AI cannot change data, needs OpenAI/Gemini or credits, has no local-model option, and is **not in the Community images** (✅ checked 19 and 20) |
| 4 | **Handover report** (10 parts) + added your **kickoff meeting** notes | `AI-ERP-Handover-Report.md` |
| 5 | **Audio briefing** (robotic voice rejected → redone with a neural voice, ~18 min) | `Project-Audio-Briefing-Human-Voice.mp3` |
| 6 | **Team plan**: roles A–D → plan without roles → **simplified roles with names** (Floyd Backend, Marija AI & Chat, Tijn Project Lead, Anastasia Tester & Writer) | `Tasks-Per-Person.pdf`, `Project-Overview.pdf`, plan files |
| 7 | **Pack for ChatGPT** (context pack + redacted source zip; secrets removed) | `ChatGPT-Context-Pack.md`, `Source-Code-Redacted.zip` |
| 8 | **Odoo 20 test** | ✅ V3 works unchanged on Odoo 20. **Odoo 20 needs PostgreSQL 16+** (15 fails) |
| 9 | **Setup kit**: seed script (14 customers, 14 products, limited `ai_agent` user), check script, docker-compose, data contract for Floyd and Marija | ✅ all tested on Odoo 20 |
| 10 | **Your PC setup, guided step by step** | see §3 |
| 11 | **First real chat test failed**; diagnosed with `curl`; **fix built and tested, not applied** | see §5 |
| 12 | This overview + the teammate quickstart | you are here |

## 3. Your PC: what is done (verified from your outputs and screenshots)

| Step | Result |
|---|---|
| Odoo installer | ✅ Odoo **20.0.20261109**, all-in-one with PostgreSQL, in `C:\Program Files\Odoo 20.0.20261109` |
| Database `odoo`, Netherlands, no demo data | ✅ created |
| Edition | ✅ **Community** (Enterprise apps show "Upgrade") |
| Apps | ✅ Sales and Invoicing active |
| Tools | ✅ Python 3.12.10, Git 2.56.0, Node 26.12.0 |
| Repo + kit | ✅ `Documents\AI-Integrated-ERP`, `setup\` folder present |
| Seed script | ✅ 14 customers, 14 products, `ai_agent` created (Odoo shows 17 contacts = 14 + AI Agent + Administrator + My Company) |
| `check_setup.py` | ✅ all Odoo checks OK; Ollama line failed only because Ollama wasn't installed yet ⚠️ (final full run not reported) |
| V3 installed and started | ✅ backend :8001, UI :5173, 144 Python packages, 145 npm packages |
| Ollama + model | ✅ Ollama **0.40.16**, `llama3.1` (4.9 GB) |
| Speed test | **Cold start about 40 s; second run about 1 s** (the first run loads the model) |
| Hardware | RTX 3070 Ti (8 GB), Ryzen 5 5600X, 64 GB RAM. The 8B model should fit entirely in the GPU ⚠️ (`ollama ps` output not seen) |

## 4. What we learned about the old group's V3 (verified)

| Problem | Evidence |
|---|---|
| **AI invents data after a failed request** | Real model, your PC: invented 10, then 3, customers that don't exist |
| Failure cause on your PC | The AI sent `fields` as **text**; Odoo error `Invalid field '['`. The code fixes this for `domain` but not `fields` |
| Errors are hidden | The screen shows only a grey "Executed" bubble |
| 2+ users at once break it | 28 of 40 parallel requests failed (shared connection) |
| Abandoned approvals freeze the server | After 40 abandoned dialogs, every new chat hung |
| Fuzzy name matching | "pep" → Pepsi, "a" → Chair, no "did you mean?" |
| AI's prices are trusted | Invoice created at 10 when the list price was 50 |
| It can read any Odoo model | Tested ✅ (the limited `ai_agent` user blocks system settings, ⚠️ but still reads all business data) |
| Orders/invoices are draft only and not linked | ✅ |
| Line breaks lost in chat | ✅ |
| Slow = the AI, not Odoo | Odoo answers in 8–200 ms; first AI request after idle ~40 s |
| Secrets in the old code/history | Odoo password, Teams webhook: **still need to be revoked** |

## 5. The fix we built (not applied)
`fix-agent-errors.patch` (`agent.py` only): converts text lists to real lists; after a failed request the **code** says "I could not do that… nothing was changed" instead of letting the AI improvise; shortens error messages; adds "never invent data" to the prompt. ✅ Tested with a scripted AI that makes the same mistakes as yours, plus the regression scenarios. ⚠️ **Not tested with the real llama3.1.** Apply with `git apply --ignore-whitespace fix-agent-errors.patch`; undo with `git checkout Application/V3/backend/agent.py`.

## 6. Decisions and ideas on the table
- **Direction:** a trustworthy invoicing slice (AI extracts, code validates, human approves, everything logged) plus a speed and model benchmark.
- **Data contract** (Floyd + Marija): the AI sends only what the user said, never Odoo IDs or field names; 12 decisions with recommended defaults; draft schema validates 9 examples ✅; ⚠️ Ollama structured output with it is untested.
- **Runner and model:** keep Ollama. `llama3.1` is only a baseline (2024). Test `qwen3:8b` and others on the same prompts; 7–9B fit your GPU, ~14B partly spill into RAM. Make the model name a setting (hard-coded in `agent.py`).
- **Odoo version:** 19 and 20 both work; use one version across the team. XML-RPC is deprecated but, per Odoo's docs, stays until Odoo 22.
- **Reproducibility:** one seed script, one check script, one backup/restore ("fast lane").

## 7. Still open (in order)
1. ☐ **Revoke** the leaked Odoo password and Teams webhook (old code).
2. ☐ Email the previous group (Odoo version, hardware, timings, licence, unpushed work).
3. ☐ Answer the open question: the **cart icon "1" next to Acme BV** in Contacts → check Sales → Orders → Quotations. Did the chat create a quotation?
4. ☐ `ollama ps` output and a full `check_setup.py` result.
5. ☐ Decide whether to **apply the patch**; re-test the three chat examples with the real model and log the result.
6. ☐ Floyd + Marija: 45-minute data-contract meeting.
7. ☐ Teammates: follow `QUICKSTART-TEAMMATES.md`, send hardware and timings.
8. ☐ Put the setup kit into the repo (on a branch) so everyone gets it with `git pull`.
9. ☐ Fix `--host` exposure and placeholder texts ("YourERP") before demoing on shared Wi-Fi.

## 8. Experiment log (started)
| # | Experiment | Result |
|---|---|---|
| 1 | `llama3.1`, trivial prompt, cold vs warm | Cold ~40 s, warm ~1 s (RTX 3070 Ti) |
| 2 | `llama3.1` via V3: "Show me all customers" | **Failed**: tool call error, AI invented customers |
| 3 | Fix for text-lists + honest failure message | Built, tested with scripted AI; real-model result pending |

## 9. Files delivered in this chat
| File | What |
|---|---|
| `AI-ERP-Handover-Report.md` | Full investigation (10 parts) |
| `ChatGPT-Context-Pack.md`, `Source-Code-Redacted.zip` | For a teammate's ChatGPT |
| `Project-Overview.pdf`, `Tasks-Per-Person.pdf` | Visual summaries |
| `Project-Audio-Briefing-Human-Voice.mp3`, `audio-script.txt` | 18-min audio |
| `Team-Plan.md`, `Team-Plan-No-Roles.md` | Older plans (the roles-with-names are in `Tasks-Per-Person.pdf`) |
| `Odoo-Setup-Kit.zip` | Guide, seed + check scripts, docker-compose, data contract |
| `Teammate-Setup-Kit.zip`, `QUICKSTART-TEAMMATES.md` | **New:** the simple teammate setup |
| `fix-agent-errors.patch` | The tested fix (not applied) |
| `fake_ollama.py`, `drive.py` | My test scripts (scripted AI + chat client) |
| `SESSION-OVERVIEW.md` | This file |

## 10. Limits to keep in mind
- I could not run Ollama or a real AI model in my environment; all code tests used a scripted stand-in. Real-model results come only from **your PC**.
- Competitor and market claims in the report come from search snippets and were not individually verified.
- The Windows installer steps follow your screenshots and Odoo's standard behaviour; I never ran the installer myself.
- Your passwords (Odoo login, master password, AI password) are **not** in any of these files. Keep them in a password manager.
