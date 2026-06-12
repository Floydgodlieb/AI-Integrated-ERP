import json
import ast
import xmlrpc.client
import re
import urllib.request
from ollama import chat, ChatResponse

# Configurations
url = 'http://localhost:8069'
db = 'odoo'
username = 'jcwm.peters@student.han.nl'
password = 'ONXwUSjlyO0Qk7'

# paste your Teams webhook URL directly here
TEAMS_WEBHOOK_URL = "https://default5d73e7b7b3e14d00b303056140b2a3.b4.environment.api.powerplatform.com:443/powerautomate/automations/direct/workflows/fcd1b2652820422e9645f70fdc68a208/triggers/manual/paths/invoke?api-version=1&sp=%2Ftriggers%2Fmanual%2Frun&sv=1.0&sig=RdFTJRaixP2o1oTVxCIY7rvbyUKt7h6vI3J68cyc_9Q"

# System authentication
try:
    common = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/common')
    uid = common.authenticate(db, username, password, {})
except Exception as e:
    print(f"❌ Something went wrong, make sure Odoo is running. Error: {str(e)}")
    exit()

if not uid:
    print("❌ Login Failed. Check credentials or Odoo instance status.")
    exit()

print("✅ Connection securely established to Odoo Instance.")
models = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/object')

def send_teams_notification(title, message, is_success=True):
    """Sends a native Adaptive Card payload to your Teams Workflows endpoint."""
    status_color = "Good" if is_success else "Attention"
    status_label = "✅ SUCCESS" if is_success else "❌ ERROR"
    
    payload = {
        "type": "message",
        "attachments": [
            {
                "contentType": "application/vnd.microsoft.card.adaptive",
                "content": {
                    "type": "AdaptiveCard",
                    "body": [
                        {
                            "type": "Container",
                            "items": [
                                {
                                    "type": "TextBlock",
                                    "size": "Medium",
                                    "weight": "Bolder",
                                    "text": f"🤖 Odoo Agent Alert: {title}"
                                },
                                {
                                    "type": "TextBlock",
                                    "text": f"Status: **{status_label}**",
                                    "color": status_color,
                                    "weight": "Bolder",
                                    "spacing": "Small"
                                },
                                {
                                    "type": "TextBlock",
                                    "text": message,
                                    "wrap": True,
                                    "spacing": "Medium"
                                }
                            ]
                        }
                    ],
                    "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
                    "version": "1.4"
                }
            }
        ]
    }
    
    try:
        req = urllib.request.Request(
            TEAMS_WEBHOOK_URL,
            data=json.dumps(payload).encode('utf-8'),
            headers={'Content-Type': 'application/json'}
        )
        with urllib.request.urlopen(req) as response:
            if response.status in [200, 202]:
                print("📢 Teams alert payload sent successfully.")
    except Exception as e:
        print(f"⚠️ Teams dispatch warning: {e}")


# Tool Schema definitions for Ollama Orchestration
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
                    'description': 'Odoo domain list of criteria, e.g. [["name","=","S00007"]]. Use [[]] for all records.'
                },
                'fields': {
                    'type': 'array',
                    'items': {'type': 'string'},
                    'description': 'Explicit list of fields to retrieve, e.g. ["name", "id"]. Never use asterisks.'
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
                    'description': 'Key-value pairs of fields to set, e.g. {"name": "John Doe"}'
                }
            },
            'required': ['model', 'values'],
            'additionalProperties': False
        }
    }
}

system_instruction = """
You are an Odoo ERP API Assistant. Your objective is to help the user manage customers, orders, and sales data.

CONVERSATIONAL RULES:
- Talk to the user normally to understand what they want to achieve.
- CRITICAL: If the user says something vague like "I want to add a sale" or "Create an invoice", DO NOT output a JSON block yet. Ask them for the missing details first (Customer, Products, Quantities).
- Only propose your structural action by outputting a valid JSON block once you have all the required variables.
- Once you receive data back from the system, interpret it and give a clear explanation.

STRICT TOOL RULES:
- Output valid tool calls matching the JSON schemas provided.
- NEVER include python-style inline comments (like # comment) inside any JSON block output. It breaks parsers.
- domain MUST be a real array list structure, not a raw string.
- NEVER use SQL commands or raw timestamps like NOW() inside the domain. Use static text dates like '2026-01-01 00:00:00' if filtering by date.
- NEVER use "*" in fields. Always return explicit field names.
- If you look up the ID of a product also get the price of the product.

Odoo model maps:
- sales orders → sale.order
- customers → res.partner
- invoices → account.move

CRITICAL FIELDS NOTICE:
- Do NOT mix sale.order and account.move fields! 
- If creating a customer invoice, use model "account.move" and set "move_type": "out_invoice". 
- Do NOT use "move_type" if the model is "sale.order".

FEW-SHOT SYNTAX EXAMPLES:
User wants a costumers information
{ "name": "odoo_search_read", "parameters": { "model": "res.partner", "domain": [["name", "ilike", "Pepsi"]], "fields": ["name", "id"] } }

User wants a Sales Order:
{"name": "odoo_create", "parameters": {"model": "sale.order", "values": {"partner_id": 72, "order_line": [[0, 0, {"product_id": 15, "product_uom_qty": 2, "price_unit": 140.00}]]}}}

User wants an Invoice:
{"name": "odoo_create", "parameters": {"model": "account.move", "values": {"partner_id": 72, "move_type": "out_invoice", "invoice_date": "2026-06-09", "invoice_line_ids": [[0, 0, {"product_id": 15, "quantity": 2, "price_unit": 140.00}]]}}}
"""

def execute_local_tool(tool_name: str, args: dict):
    """Executes the specific Odoo function using the XML-RPC client wrapper."""
    if tool_name == "odoo_search_read":
        domain = args["domain"]
        if isinstance(domain, str):
            try:
                domain = ast.literal_eval(domain)
            except:
                domain = []

        if len(domain) == 0 or domain == [[]]:
            domain = []

        print(f"🔧 [Executing ERP Read] Model: {args['model']} | Domain: {domain}")
        result = models.execute_kw(
            db, uid, password,
            args["model"],
            "search_read",
            [domain],
            {"fields": args["fields"]}
        )
        return result

    elif tool_name == "odoo_create":
        print(f"📤 [Executing ERP Create] Model: {args['model']}")
        
        # --- AUTO-CORRECTION LAYER FOR SALES ORDERS ---
        if args['model'] == 'sale.order' and 'order_line' in args['values']:
            raw_lines = args['values']['order_line']
            if raw_lines and isinstance(raw_lines, list):
                for line in raw_lines:
                    if isinstance(line, list) and len(line) == 3 and isinstance(line[2], dict):
                        line_data = line[2]
                        if 'quantity' in line_data:
                            line_data['product_uom_qty'] = line_data.pop('quantity')

        # --- AUTO-CORRECTION LAYER FOR INVOICES ---
        if args['model'] == 'account.move' and 'invoice_line_ids' in args['values']:
            raw_lines = args['values']['invoice_line_ids']
            if raw_lines and isinstance(raw_lines, list):
                if not isinstance(raw_lines[0], list):
                    args['values']['invoice_line_ids'] = [[0, 0, line] if isinstance(line, dict) else line for line in raw_lines]
                for line in args['values']['invoice_line_ids']:
                    if isinstance(line, list) and len(line) == 3 and isinstance(line[2], dict):
                        line_data = line[2]
                        if 'product_uom_qty' in line_data:
                            line_data['quantity'] = line_data.pop('product_uom_qty')

        # Run creation on local instance
        new_id = models.execute_kw(
            db, uid, password,
            args["model"],
            "create",
            [args["values"]]
        )
        
        # Dispatch success out to Microsoft Teams
        send_teams_notification(
            title=f"ERP Record Created: {args['model']}",
            message=f"Successfully generated a new entry under **{args['model']}** with Database ID: `{new_id}`.",
            is_success=True
        )
        return {"status": "success", "created_id": new_id}
        
    raise ValueError(f"Unknown tool target execution requested: {tool_name}")

def run_odoo_agent():
    conversation_history = [
        {'role': 'system', 'content': system_instruction}
    ]

    print("\n🤖 [Odoo Conversational Agent Active] Ask a question or submit an order modification request!")

    while True:
        try:
            user_input = input("\nYou: ").strip()
        except (KeyboardInterrupt, EOFError):
            break

        if user_input.lower() in ['exit', 'quit']:
            print("Exiting ERP assistant session.")
            break

        if not user_input:
            continue

        # 🎯 MANUAL OVERRIDE INTERCEPTOR
        if user_input.lower() in ['run', 'fetch']:
            print("\n⚡ [Manual Override] Intercepting keyword command... Locating last AI tool parameters...")
            
            last_ai_json_message = None
            for msg in reversed(conversation_history):
                if msg['role'] == 'assistant' and '"name":' in msg['content']:
                    last_ai_json_message = msg['content']
                    break
            
            if last_ai_json_message:
                try:
                    json_match = re.search(r'\{.*\}', last_ai_json_message, re.DOTALL)
                    
                    if json_match:
                        clean = json_match.group(0)
                        clean = re.sub(r'#.*$', '', clean, flags=re.MULTILINE) # Strip comments
                        clean = clean.replace("'", '"')
                        clean = re.sub(r'"domain":\s*"(\[\s*\[.*?\]\s*\])"', r'"domain": \1', clean)
                        
                        extracted_json = json.loads(clean)
                        tool_name = extracted_json.get("name")
                        args = extracted_json.get("parameters") or extracted_json.get("arguments", {})
                        
                        if "fields" in args and ("*" in args["fields"] or not args["fields"]):
                            args["fields"] = ["name", "id"]
                        
                        tool_result = execute_local_tool(tool_name, args)
                        
                        conversation_history.append({
                            'role': 'tool',
                            'content': json.dumps(tool_result, default=str),
                            'name': tool_name
                        })
                        
                        print("🔄 [System] Live Odoo data fetched! Asking AI to interpret results...")
                        
                        response = chat(model='llama3.1', messages=conversation_history)
                        ai_reply = response.message.content
                        print(f"\nAI: {ai_reply}")

                        conversation_history.append({'role': 'assistant', 'content': ai_reply})
                        continue
                    else:
                        print("❌ No valid structural JSON boundaries found in the previous assistant message.")
                except Exception as e:
                    error_msg = str(e)
                    print(f"❌ Failed to execute manual shortcut payload: {error_msg}")
                    
                    # Dispatch error out to Microsoft Teams
                    send_teams_notification(
                        title=f"ERP Execution Failure",
                        message=f"An action failed to process on the Odoo backend.\n\n**Error Trace:**\n`{error_msg[:250]}...`",
                        is_success=False
                    )
                continue
            else:
                print("❌ There is no previous AI tool proposal found in chat memory context.")
                continue

        # Regular conversational chat flow
        conversation_history.append({'role': 'user', 'content': user_input})
        
        print("\n[AI] Processing data tracking state...")
        response: ChatResponse = chat(
            model='llama3.1',
            messages=conversation_history,
            tools=[odoo_search_read_tool, odoo_create_tool]
        )
        
        ai_reply = response.message.content or ""
        print(f"\nAI: {ai_reply}")
        conversation_history.append({'role': 'assistant', 'content': ai_reply})

if __name__ == "__main__":
    run_odoo_agent()