from ollama import chat, ChatResponse
import json
import ast
import xmlrpc.client
import datetime

debug = True

if debug:
    start = datetime.datetime.now()
    print(F"⏱️  Start time", start.strftime('%Y-%m-%d %H:%M:%S') )

url = 'http://localhost:8069'
db = 'odoo'
username = 'jcwm.peters@student.han.nl'
password = 'ONXwUSjlyO0Qk7'

if debug:
    print(f"⚠️  Login attempt", str(datetime.datetime.now()) )
common = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/common')
uid = common.authenticate(db, username, password, {})

if not uid:
    if debug:
        print(F"❌ Login Failed", str(datetime.datetime.now()) )
    exit()

if debug:
    print(f"✅ Login succesfull", str(datetime.datetime.now()) )

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

odoo_create_tool = {
    'type': 'function',
    'function': {
        'name': 'odoo_create',
        'description': 'Add a new record in Odoo and return its database identifier.',
        'parameters': {
            'type': 'object',
            'properties': {
                'model': {
                    'type': 'string',
                    'description': 'Odoo model, e.g. res.partner'
                },
                'values': {
                    'type': 'object',
                    'description': 'Key-value pairs of the fields to set, e.g. {"name": "John Doe"}'
                }
            },
            'required': ['model', 'values'],
            'additionalProperties': False
        }
    }
}

if debug:
    print(f"⚠️  Instruction giving", str(datetime.datetime.now()) )

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
if debug:
    print(f"⚠️  User input", str(datetime.datetime.now()) )   

user_input = "I want to add a costumer called Doofenshmirtz Evil Incorporated. The email is DoofenshmirtzEI@gmail.com and cellphone is 0612345678."

if debug:
    print(f"⚠️  Respons starting",str(datetime.datetime.now()))
response: ChatResponse = chat(
    model='llama3.1',
    messages=[
        {'role': 'system', 'content': system_instruction},
        {'role': 'user', 'content': user_input}
    ],
    tools=[odoo_search_read_tool, odoo_create_tool]
)
if debug:
    end = datetime.datetime.now()
    print(f"⚠️  Tools", end.strftime('%Y-%m-%d %H:%M:%S'))

if response.message.tool_calls:
    for call in response.message.tool_calls:
        tool_name = call.function.name
        args = call.function.arguments
        
        if debug:
            print("\n🔧 Tool used:", call.function.name)
            print("Raw args:", args)

        if tool_name == "odoo_search_read":
            domain = args["domain"]
            if isinstance(domain, str):
                domain = ast.literal_eval(domain)

            result = models.execute_kw(
                db, uid, password,
                args["model"],
                "search_read",
                [domain],
                {"fields": args["fields"]}
            )
            print("\n🎉 SEARCH RESULT:")
            print(json.dumps(result, indent=2, default=str))

        elif tool_name == "odoo_create":

            new_id = models.execute_kw(
                db, uid, password,
                args["model"],
                "create",
                [args["values"]]
            )

            print(f"\n🎉 CREATE RESULT: Created record with ID {new_id}")

else:
    if debug:
        print("❌ No tool used")
    print(response.message.content)

if debug:
    duration = end - start
    print("\n--- ⏱️  Performance Summary ---")
    print(f"Start Time: {start.strftime('%H:%M:%S.%f')}")
    print(f"End Time:   {end.strftime('%H:%M:%S.%f')}")
    print(f"Total Execution Time: {duration.total_seconds():.1f} seconds")