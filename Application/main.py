from ollama import chat, ChatResponse
import json
import ast
import xmlrpc.client

# =========================
# ODOO CONFIG
# =========================
url = 'http://localhost:8069'
db = 'odoo'
username = 'jcwm.peters@student.han.nl'
password = 'ONXwUSjlyO0Qk7'

common = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/common')
uid = common.authenticate(db, username, password, {})

if not uid:
    print("❌ Login mislukt")
    exit()

print(f"✅ Ingelogd (UID: {uid})")

models = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/object')

odoo_search_read_tool = {
    'type': 'function',
    'function': {
        'name': 'odoo_search_read',
        'description': 'Search for records in Odoo and read their fields.',
        'parameters': {
            'type': 'object',
            'properties': {
                'model': {
                    'type': 'string',
                    'description': 'Odoo model, e.g. sale.order'
                },
                'domain': {
                    'type': 'array',
                    'items': {
                        'type': 'array',
                        'items': {'type': 'string'}
                    },
                    'description': 'Odoo domain, e.g. [["name","=","S00007"]]'
                },
                'fields': {
                    'type': 'array',
                    'items': {'type': 'string'},
                    'description': 'Fields to retrieve'
                }
            },
            'required': ['model', 'domain', 'fields'],
            'additionalProperties': False
        }
    }
}

system_instruction = """
You are an Odoo API Assistant.

You MUST always use the tool when data is requested.

STRICT RULES:
- Output ONLY valid tool calls
- NEVER return JSON as text
- domain MUST be a real array, not a string
- NEVER wrap arrays in quotes

Odoo models:
- sale orders → sale.order
- customers → res.partner
- invoices → account.move

Domain format:
[["field", "operator", "value"]]

Example:
S00007 → [["name", "=", "S00007"]]

NEVER use "*" in fields.
Always return explicit field names.

For sale.order always use:
["name", "partner_id", "amount_total", "state"]
"""

user_input = "I want to see details about sale S00007"

response: ChatResponse = chat(
    model='llama3.1',
    messages=[
        {'role': 'system', 'content': system_instruction},
        {'role': 'user', 'content': user_input}
    ],
    tools=[odoo_search_read_tool]
)

if response.message.tool_calls:
    for call in response.message.tool_calls:
        args = call.function.arguments

        print("\n🔧 Tool used:", call.function.name)
        print("Raw args:", args)

        domain = args["domain"]

        # Fix if LLM outputs string instead of list
        if isinstance(domain, str):
            domain = ast.literal_eval(domain)

        result = models.execute_kw(
            db, uid, password,
            args["model"],
            "search_read",
            [domain],
            {"fields": args["fields"]}
        )

        print("\n📊 RESULT:")
        print(json.dumps(result, indent=2, default=str))

else:
    print("❌ No tool used")
    print(response.message.content)