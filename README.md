# AI-Integrated-ERP

## Versions in this repository
| Folder | What | Status |
|---|---|---|
| `Application/V1`, `Application/V2` | Previous group's early prototypes (contain leaked credentials – never reuse them) | Archive |
| `Application/V3` | Previous group's final version, **unchanged** (kept for before/after comparison) | Archive |
| `Application/V3.1` | **Our current version**: V3 with a hardened backend (safe Odoo access, prices from Odoo, expiring approvals, audit log, tests) | **Use this** |

Start here: `Setup/Quickstart.md` (setup), `documentation/BACKEND-CHANGES.md` (what changed), `documentation/EXPERIMENT-LOG.md` (measurements).

---

Project Charter: Minor Data Driven Decision Making
(M3DM)
Project Name: AI-Integrated ERP (“Invisible ERP”)

# Introduction
In this project we will focus on making a ERP system that uses a LLM (Large Launguege Model) to update the ERP system. In the end you can tell the LLM that you have made a sale of '50 chairs to L.Luther' and that be updated in the ERP Database.

The ERP system that we will use for this project is a open source system called Odoo (https://github.com/odoo/odoo)

# Plan
The plan is to make a AI chat bot to where you can tell the things you have done, like you made a sale. The bot will interpet that into a format of a JSON statement. That statement will get sent to the correct endpoint via HTTPS. 

The response will get sent back to the user via the AI chat bot.