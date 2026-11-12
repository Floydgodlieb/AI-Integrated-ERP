import json
import ast
import os
import threading
from ollama import chat as ollama_chat

# How long the backend waits for the user to click approve/decline before giving up.
# Before this setting, an unanswered approval blocked a server thread forever.
APPROVAL_TIMEOUT_SECONDS = int(os.getenv("APPROVAL_TIMEOUT_SECONDS", "300"))

system_instruction = """
You are an Odoo ERP API Assistant. Your objective is to help the user manage customers, orders, and sales data.

CONVERSATIONAL RULES:
- Talk to the user normally to understand what they want to achieve.
- If the user says something vague like "I want to add a sale" or "Create an invoice", ask them for the missing details first (Customer, Products, Quantities).
- When you receive tool results from the system, summarize them conversationally. Do NOT output raw JSON or tool call syntax.
- Keep responses concise and natural. List data in a readable way, not as code blocks.

STRICT TOOL RULES:
- domain MUST be a real array list structure, not a raw string.
- NEVER use SQL commands or raw timestamps like NOW() inside the domain. Use static text dates like '2026-01-01 00:00:00' if filtering by date.
- NEVER use "*" in fields. Always return explicit field names.

ENTITY RESOLUTION RULE:
- When creating records, pass customer names and product names as plain strings — NOT IDs.
- The system will automatically look up the correct IDs for you.
- Example: use "partner_id": "Pepsi" instead of "partner_id": 73
- Example: use "product_id": "Chair Floor Protection" instead of "product_id": 2

Odoo model maps:
- sales orders -> sale.order
- customers -> res.partner
- invoices -> account.move

CRITICAL FIELDS NOTICE:
- Do NOT mix sale.order and account.move fields!
- If creating a customer invoice, use model "account.move" and set "move_type": "out_invoice".
- Do NOT use "move_type" if the model is "sale.order".
"""

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

TOOLS = [odoo_search_read_tool, odoo_create_tool]

FIELD_MODEL_MAP = {
    "partner_id": "res.partner",
    "product_id": "product.product",
    "user_id": "res.users",
}

MODEL_LABELS = {
    "sale.order": "Sales Order",
    "res.partner": "Customer",
    "account.move": "Invoice",
    "product.product": "Product",
}

NESTED_LINE_FIELDS = {"order_line", "invoice_line_ids"}


class ConversationAgent:
    def __init__(self, odoo_client):
        self.odoo = odoo_client
        self.conversations = {}
        self.pending_confirms = {}
        self.pending_events = {}

    def set_confirmation(self, conv_id: str, approved: bool):
        if conv_id in self.pending_confirms:
            self.pending_confirms[conv_id]["approved"] = approved
            if conv_id in self.pending_events:
                self.pending_events[conv_id].set()

    def cancel_pending(self, conv_id: str, reason: str = "cancelled"):
        """Release a waiting approval (e.g. the browser closed) so its server thread is freed."""
        pending = self.pending_confirms.get(conv_id)
        if pending is not None and pending.get("approved") is None:
            pending["approved"] = False
            pending["reason"] = reason
            event = self.pending_events.get(conv_id)
            if event is not None:
                event.set()

    def discard_pending(self, conv_id: str, reason: str = "cancelled"):
        """Remove an approval nobody will wait for anymore (its chat stream was closed)."""
        pending = self.pending_confirms.pop(conv_id, None)
        self.pending_events.pop(conv_id, None)
        if pending is not None:
            self._audit("approval_expired", conv_id=conv_id, reason=reason)

    def _audit(self, event: str, **data):
        audit = getattr(self.odoo, "audit", None)
        if audit is not None:
            audit.write(event, **data)

    def get_or_create_history(self, conv_id: str) -> list:
        if conv_id not in self.conversations:
            self.conversations[conv_id] = [
                {'role': 'system', 'content': system_instruction}
            ]
        return self.conversations[conv_id]

    def get_history(self, conv_id: str) -> list | None:
        return self.conversations.get(conv_id)

    def clear_history(self, conv_id: str):
        self.conversations.pop(conv_id, None)

    def execute_search_read(self, args: dict):
        domain = args.get("domain", [])
        if isinstance(domain, str):
            try:
                domain = ast.literal_eval(domain)
            except Exception:
                domain = []
        fields = args.get("fields", ["name", "id"])
        if not fields or "*" in fields:
            fields = ["name", "id"]
        return self.odoo.search_read(args["model"], domain, fields)

    def execute_create(self, args: dict):
        def strip_resolved(val):
            if isinstance(val, dict):
                return {k: strip_resolved(v) for k, v in val.items() if not k.startswith("_")}
            if isinstance(val, list):
                return [strip_resolved(item) for item in val]
            return val

        clean_values = strip_resolved(args.get("values", {}))
        return self.odoo.create(args["model"], clean_values)

    def normalize_structure(self, values: dict, model: str) -> dict:
        values = dict(values)
        if model == "sale.order":
            if "product_id" in values and "order_line" not in values:
                line = {}
                for field in ("product_id", "product_uom_qty", "quantity", "price_unit"):
                    if field in values:
                        line[field] = values.pop(field)
                if line.get("quantity") is not None and "product_uom_qty" not in line:
                    line["product_uom_qty"] = line.pop("quantity")
                if line:
                    values["order_line"] = [[0, 0, line]]
            if "partner_id" in values and isinstance(values.get("partner_id"), str):
                pass
        if model == "account.move":
            if "product_id" in values and "invoice_line_ids" not in values:
                line = {}
                for field in ("product_id", "quantity", "price_unit", "product_uom_qty"):
                    if field in values:
                        line[field] = values.pop(field)
                if line.get("product_uom_qty") is not None and "quantity" not in line:
                    line["quantity"] = line.pop("product_uom_qty")
                if line:
                    values["invoice_line_ids"] = [[0, 0, line]]
        return values

    def resolve_entities(self, values: dict, model: str = None) -> dict:
        resolved = {}
        for field, raw_value in values.items():
            if field in NESTED_LINE_FIELDS and isinstance(raw_value, list):
                resolved_lines = []
                for item in raw_value:
                    if isinstance(item, list) and len(item) == 3:
                        resolved_lines.append([item[0], item[1], self.resolve_entities(item[2], model)])
                    elif isinstance(item, dict):
                        resolved_lines.append(self.resolve_entities(item, model))
                    else:
                        resolved_lines.append(item)
                resolved[field] = resolved_lines
            elif field in FIELD_MODEL_MAP and isinstance(raw_value, str):
                search_model = FIELD_MODEL_MAP[field]
                results = self.odoo.search_read(search_model, [["name", "ilike", raw_value]], ["name", "id"])
                if not results:
                    raise ValueError(f"Could not find {search_model} matching '{raw_value}'")
                resolved[field] = results[0]["id"]
                resolved[f"_resolved_{field}_name"] = results[0]["name"]
            else:
                resolved[field] = raw_value
        return resolved

    def _summarize_create(self, model: str, values: dict) -> str:
        label = MODEL_LABELS.get(model, model)
        parts = [f"Create {label}"]
        if "partner_id" in values:
            name = values.get("_resolved_partner_id_name")
            parts.append(f"Customer: {name or values['partner_id']}")
        if "order_line" in values and isinstance(values["order_line"], list):
            qty = len(values["order_line"])
            parts.append(f"{qty} product line(s)")
        elif "invoice_line_ids" in values and isinstance(values["invoice_line_ids"], list):
            qty = len(values["invoice_line_ids"])
            parts.append(f"{qty} invoice line(s)")
        for k, v in values.items():
            if k.startswith("_"):
                continue
            if k in ("partner_id", "order_line", "invoice_line_ids"):
                continue
            if k == "name":
                parts.append(f"Name: {v}")
            elif k == "move_type":
                parts.append(f"Type: {v}")
            elif k == "product_id":
                name = values.get("_resolved_product_id_name")
                parts.append(f"Product: {name or v}")
            elif isinstance(v, (int, float)) and not isinstance(v, bool):
                parts.append(f"{k}: {v}")
            elif isinstance(v, str) and len(str(v)) < 40:
                parts.append(f"{k}: {v}")
        return " | ".join(parts)

    def chat_stream(self, conv_id: str, user_message: str):
        history = self.get_or_create_history(conv_id)
        history.append({'role': 'user', 'content': user_message})

        yield {"type": "status", "content": "Thinking..."}

        response = ollama_chat(
            model='llama3.1',
            messages=history,
            tools=TOOLS
        )

        if response.message.tool_calls:
            for tc in response.message.tool_calls:
                tool_name = tc.function.name
                tool_args = tc.function.arguments

                if tool_name == "odoo_create":
                    try:
                        raw_model = tool_args.get("model", "")
                        normalized = self.normalize_structure(tool_args.get("values", {}), raw_model)
                        resolved_values = self.resolve_entities(normalized, raw_model)
                        tool_args["values"] = resolved_values
                    except ValueError as e:
                        tool_result = {"error": str(e)}
                        history.append({
                            'role': 'tool',
                            'content': json.dumps(tool_result, default=str),
                            'name': tool_name
                        })
                        yield {"type": "tool_call", "content": json.dumps({"name": tool_name, "result": tool_result}, default=str)}
                        continue

                    summary = self._summarize_create(tool_args.get("model", ""), tool_args.get("values", {}))
                    event = threading.Event()
                    self.pending_events[conv_id] = event
                    self.pending_confirms[conv_id] = {
                        "approved": None,
                        "tool_name": tool_name,
                        "tool_args": tool_args
                    }
                    self._audit("approval_requested", conv_id=conv_id, model=tool_args.get("model", ""),
                                summary=summary, user_message=user_message)
                    yield {"type": "confirmation_required", "content": json.dumps({
                        "summary": summary,
                        "model": tool_args.get("model", ""),
                        "values": tool_args.get("values", {})
                    }, default=str)}

                    answered = event.wait(timeout=APPROVAL_TIMEOUT_SECONDS)

                    pending = self.pending_confirms.pop(conv_id, None) or {}
                    self.pending_events.pop(conv_id, None)
                    approved = bool(answered and pending.get("approved"))

                    if approved:
                        yield {"type": "status", "content": "Executing create..."}
                        try:
                            tool_result = self.execute_create(tool_args)
                        except Exception as e:
                            tool_result = {"error": str(e)}
                    elif not answered or pending.get("reason"):
                        reason = pending.get("reason") or "timeout"
                        self._audit("approval_expired", conv_id=conv_id, reason=reason)
                        tool_result = {"status": "expired",
                                       "message": "No approval was given in time. Nothing was created."}
                    else:
                        tool_result = {"status": "cancelled", "message": "User declined the create operation"}

                    history.append({
                        'role': 'tool',
                        'content': json.dumps(tool_result, default=str),
                        'name': tool_name
                    })
                    yield {"type": "tool_call", "content": json.dumps({"name": tool_name, "result": tool_result}, default=str)}

                else:
                    try:
                        tool_result = self.execute_search_read(tool_args)
                    except Exception as e:
                        tool_result = {"error": str(e)}
                    history.append({
                        'role': 'tool',
                        'content': json.dumps(tool_result, default=str),
                        'name': tool_name
                    })
                    yield {"type": "tool_call", "content": json.dumps({"name": tool_name, "result": tool_result}, default=str)}

            yield {"type": "status", "content": "Interpreting results..."}

            stream = ollama_chat(
                model='llama3.1',
                messages=history,
                stream=True
            )

            full_content = ""
            for chunk in stream:
                if chunk.message and chunk.message.content:
                    full_content += chunk.message.content
                    yield {"type": "token", "content": chunk.message.content}

            history.append({'role': 'assistant', 'content': full_content})
        else:
            text = response.message.content or ""
            yield {"type": "token", "content": text}
            history.append({'role': 'assistant', 'content': text})

        yield {"type": "done", "content": ""}
