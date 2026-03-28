# AI-Integrated-ERP

Project Charter: Minor Data Driven Decision Making
(M3DM)
Project Name: AI-Integrated ERP (“Invisible ERP”)

# Introduction
In this project we will focus on making a ERP system that uses a LLM (Large Launguege Model) to update the ERP system. In the end you can tell the LLM that you have made a sale of '50 chairs to L.Luther' and that be updated in the ERP Database.

The ERP system that we will use for this project is a open source system called Odoo (https://github.com/odoo/odoo)

# Plan
The plan is to make a AI chat bot to where you can tell the things you have done, like you made a sale. The bot will interpet that into a format of a JSON statement. That statement will get sent to the correct endpoint via HTTPS. 

The response will get sent back to the user via the AI chat bot.