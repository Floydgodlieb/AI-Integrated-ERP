# V1 Documentation

Version 1 gives us the needed validation of what can be done and what needs more work.
What does the code do?

In V1, the first thing that is done after including all needed libraries is connecting to the locally hosted Odoo. This is needed for being able to connect and validate the user. Without it, you can't do anything. This was done by changing the command given by Odoo itself to give Docker a local port to take.
## 1. Authentication & Connection

The script uses the xmlrpc.client to communicate with Odoo’s external API. By providing the url, db, username, and password, it retrieves a User ID (UID). This UID acts as the session token for all subsequent data requests, ensuring that the AI only interacts with data it is authorized to see.
## 2. Defining the Tool (Function Calling)

A core part of V1 is the odoo_search_read_tool definition. Instead of just asking the AI to "find info," we provide it with a strict JSON Schema. This schema explains:

    The Function Name: odoo_search_read.

    The Parameters: It defines exactly what arguments the AI must generate (Model, Domain, and Fields).

    Validation: It forces the AI to output structured data that our Python script can understand.

## 3. System Instructions & Constraints

To prevent the AI from "hallucinating" or giving conversational answers when we need data, we use a system_instruction.

    Formatting Rules: It forces the AI to use specific Odoo syntax (like the domain list format).

    Model Mapping: It teaches the AI that "customers" refers to the res.partner model and "sales" refers to sale.order.

    Field Selection: It ensures the AI always asks for essential fields like amount_total or state to keep the output consistent.

## 4. The Processing Loop

Once the user enters a prompt (e.g., "I want to see details about sale S00007"), the following flow occurs:

    AI Analysis: The Llama 3.1 model recognizes the intent and generates a Tool Call instead of a text response.

    Argument Parsing: The script intercepts this call and extracts the search criteria.

    Odoo Execution: The script calls models.execute_kw using the search_read method. This is where the actual database query happens.

    Data Feedback: The raw data from Odoo is returned and printed in a readable JSON format.