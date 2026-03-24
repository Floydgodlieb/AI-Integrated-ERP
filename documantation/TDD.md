# Technical Design Document

By reading this file you will get a clue on what will be done this project.

## 1. Product overview

### 1.1 Purpose
The purpose of this project is to take the next step in the field of ERPs and combine it with AI. The goal of the project is to have no need for the user interface, this is where the AI will step up.

By working with a large launguege model the user will be able to tell the AI what sales or updates has been made. The AI will handle those changes to keep the system up-to date.

### 1.2 Scope

- ERP system (Odoo.com)
- Database
- Chat system to AI model
- Local AI model (Meta.com)
- Middleware

## 2. System architecture

### 2.1 High level architecture

* CLI interface: The user of the AI will need to be able to text with the model. This will be done by a CLI (Command line interface), so a user can give updates to the model.
* ERP system: The system that will be used in this project is a open source project called Odoo.com. This makes it so there won't be any need to develop a ERP from scratch.
* RestAPI: There is a need for the Cli to be connected to the ERP system. This can be done via RestAPI endpoints.
* Middleware to translate costumer name to costumer_id 

## 3. Technical strategy

### 3.1 AI strategy
The AI model will be used to interpret the message that got send to him. It will read it and form a SQL statement or a HTTP/HTTPS request made with JSON out of it. This will use a API to let both communicate with eachother. 

Authentication is a problem to tackel. There ERP system of Odoo.com has it's own security where we have to deal with.

## 4. Risk management

There are some risks involed with this project. 

* LLM Hallucination: We don't want the LLM to guess about things or delete records that should'v been kept.
* Security permission: Cross origin request are default for browser to keep one site to act on other sites.
* Data: There can't be any duplications in the data. This includes costumers and products.
* Middleware: Needs a good try catch in case of a hallucination or human error