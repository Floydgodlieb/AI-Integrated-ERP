import copy
import json
import ast
import os
import re
import threading
import time
from datetime import date
from ollama import chat as ollama_chat

# How long the backend waits for the user to click approve/decline before giving up.
# Before this setting, an unanswered approval blocked a server thread forever.
APPROVAL_TIMEOUT_SECONDS = int(os.getenv("APPROVAL_TIMEOUT_SECONDS", "300"))

system_instruction = """Turn each user request into one structured Odoo action.

- Send customer and product names with quantities. Never send Odoo IDs or prices.
- Use a named lookup for ERP facts. Never invent customers, products, prices, or results.
- Ask one short question if required details are missing or unclear.
- Prepare only draft customer invoices and sales orders. The backend checks names and prices.
- Never post, pay, delete, or update records. Refuse unsupported requests.
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

def _tool(name: str, description: str, properties: dict, required: list[str]) -> dict:
    return {
        "type": "function",
        "function": {
            "name": name,
            "description": description,
            "parameters": {
                "type": "object",
                "properties": properties,
                "required": required,
                "additionalProperties": False,
            },
        },
    }


LINE_PROPERTIES = {
    "product_name": {"type": "string", "description": "Product name, not an Odoo ID."},
    "quantity": {"type": "number", "exclusiveMinimum": 0},
}
LINE_SCHEMA = {
    "type": "object",
    "properties": LINE_PROPERTIES,
    "required": ["product_name", "quantity"],
    "additionalProperties": False,
}

TOOLS = [
    _tool("create_invoice", "Prepare a draft customer invoice after checking its details.", {
        "customer_name": {"type": "string", "minLength": 1},
        "lines": {"type": "array", "minItems": 1, "items": LINE_SCHEMA},
        "invoice_date": {"type": ["string", "null"], "description": "ISO date YYYY-MM-DD, or null."},
    }, ["customer_name", "lines", "invoice_date"]),
    _tool("create_sales_order", "Prepare a draft sales order after checking its details.", {
        "customer_name": {"type": "string", "minLength": 1},
        "lines": {"type": "array", "minItems": 1, "items": LINE_SCHEMA},
    }, ["customer_name", "lines"]),
    _tool("lookup_records", "Look up customers, products, sales orders, or customer invoices.", {
        "what": {"type": "string", "enum": ["customers", "products", "sales_orders", "invoices"]},
        "search_text": {"type": ["string", "null"]},
        "limit": {"type": "integer", "minimum": 1, "maximum": 50},
    }, ["what", "search_text", "limit"]),
    _tool("ask_clarification", "Ask one short question when required information is missing.", {
        "question": {"type": "string", "minLength": 1},
    }, ["question"]),
    _tool("refuse_request", "Refuse unsupported actions or access to unsupported data.", {
        "reason": {"type": "string", "minLength": 1},
    }, ["reason"]),
]


class _Function:
    def __init__(self, name: str, arguments: dict):
        self.name = name
        self.arguments = arguments


class _ToolCall:
    def __init__(self, name: str, arguments: dict):
        self.function = _Function(name, arguments)

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

LOOKUP_CONFIG = {
    "customers": ("res.partner", ["id", "name", "email", "city"]),
    "products": ("product.product", ["id", "name", "default_code", "list_price"]),
    "sales_orders": ("sale.order", ["id", "name", "partner_id", "state", "amount_total"]),
    "invoices": ("account.move", ["id", "name", "partner_id", "invoice_date", "state", "amount_total"]),
}


class AmbiguousName(ValueError):
    """Several Odoo records match a name; the user picks one in the next message."""

    def __init__(self, field: str, raw: str, label: str, candidates: list):
        self.field, self.raw, self.candidates = field, raw, candidates
        options = "\n".join(f"{i}. {c['name']}" for i, c in enumerate(candidates, 1))
        super().__init__(f"More than one {label} matches '{raw}':\n{options}\n"
                         f"Reply with the number or the full name.")


class ConversationAgent:
    def __init__(self, odoo_client):
        self.odoo = odoo_client
        self.conversations = {}
        self.pending_confirms = {}
        self.pending_events = {}
        self.pending_choices = {}   # conv_id -> request waiting for the user to pick a name

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
        self.pending_choices.pop(conv_id, None)

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
        limit = args.get("limit")
        if isinstance(limit, int) and not isinstance(limit, bool):
            return self.odoo.search_read(args["model"], domain, fields, limit=limit)
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

    def resolve_entities(self, values: dict, model: str = None, choices: dict | None = None) -> dict:
        resolved = {}
        for field, raw_value in values.items():
            if field in NESTED_LINE_FIELDS and isinstance(raw_value, list):
                resolved_lines = []
                for item in raw_value:
                    if isinstance(item, list) and len(item) == 3:
                        resolved_lines.append([item[0], item[1], self.resolve_entities(item[2], model, choices)])
                    elif isinstance(item, dict):
                        resolved_lines.append(self.resolve_entities(item, model, choices))
                    else:
                        resolved_lines.append(item)
                resolved[field] = resolved_lines
            elif field in FIELD_MODEL_MAP and isinstance(raw_value, str):
                search_model = FIELD_MODEL_MAP[field]
                # Exact name (any case) wins; else one partial match; several matches -> ask, never guess.
                # shortcut: % and _ in the name act as wildcards in =ilike, escape them if names ever contain them
                picked = (choices or {}).get((field, raw_value.strip().lower()))
                results = [picked] if picked else \
                    self.odoo.search_read(search_model, [["name", "=ilike", raw_value]], ["name", "id"])
                if not results:
                    results = self.odoo.search_read(search_model, [["name", "ilike", raw_value]], ["name", "id"])
                if not results:
                    raise ValueError(f"Could not find {search_model} matching '{raw_value}'")
                if len(results) > 1:
                    label = MODEL_LABELS.get(search_model, search_model).lower()
                    # shortcut: only the first 5 matches are offered; a longer list needs a search box in the chat
                    raise AmbiguousName(field, raw_value, label, results[:5])
                resolved[field] = results[0]["id"]
                resolved[f"_resolved_{field}_name"] = results[0]["name"]
            else:
                resolved[field] = raw_value
        return resolved

    def _take_choice(self, conv_id: str, user_message: str):
        """If the last reply asked 'which one?', and this message is a listed number or name, continue that request."""
        pending = self.pending_choices.pop(conv_id, None)
        if not pending:
            return None
        answer = user_message.strip().rstrip(".").lower()
        for i, candidate in enumerate(pending["candidates"], 1):
            if answer in (str(i), candidate["name"].lower()):
                key = (pending["field"], pending["raw"].strip().lower())
                return pending["tool_args"], {**pending["choices"], key: candidate}
        return None   # anything else is a new request

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

    def _lookup_args(self, args: dict) -> dict:
        what = args.get("what")
        if what not in LOOKUP_CONFIG:
            raise ValueError("Choose customers, products, sales orders, or invoices to search.")

        model, fields = LOOKUP_CONFIG[what]
        search_text = args.get("search_text")
        if search_text is not None and not isinstance(search_text, str):
            raise ValueError("Search text must be a name or reference.")
        limit = args.get("limit", 10)
        if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 50:
            raise ValueError("Search limit must be between 1 and 50.")

        if what == "customers":
            domain = [["customer_rank", ">", 0]]
            if search_text:
                domain.extend(["|", ["name", "ilike", search_text], ["city", "ilike", search_text]])
        elif what == "products":
            domain = ["|", ["name", "ilike", search_text], ["default_code", "ilike", search_text]] if search_text else []
        else:
            domain = [["name", "ilike", search_text]] if search_text else []

        return {"model": model, "domain": domain, "fields": fields, "limit": limit}

    def _map_intent(self, name: str, args: dict, user_message: str):
        if not isinstance(args, dict):
            return None, "I couldn't read that request. Please try saying it another way."

        if name == "ask_clarification":
            question = args.get("question")
            return None, question.strip() if isinstance(question, str) and question.strip() else "What would you like me to do in Odoo?"
        if name == "refuse_request":
            reason = args.get("reason")
            return None, reason.strip() if isinstance(reason, str) and reason.strip() else "I can't do that action in this app."
        if name == "lookup_records":
            try:
                return "odoo_search_read", self._lookup_args(args)
            except ValueError as error:
                return None, str(error)

        # The old names remain accepted for the scripted Ollama stand-in.
        if name in {"odoo_create", "odoo_search_read"}:
            return name, args
        if name not in {"create_invoice", "create_sales_order"}:
            return None, "I couldn't understand that request. Nothing was changed."

        customer = args.get("customer_name")
        lines = args.get("lines")
        if not isinstance(customer, str) or not customer.strip():
            return None, "Which customer should I use?"
        if not isinstance(lines, list) or not lines:
            return None, "Which product and quantity should I include?"

        values = {"partner_id": customer.strip()}
        invoice_date = args.get("invoice_date")
        if name == "create_invoice" and invoice_date:
            if not isinstance(invoice_date, str):
                return None, "Please provide the invoice date as YYYY-MM-DD."
            try:
                date.fromisoformat(invoice_date)
            except ValueError:
                return None, "Please provide the invoice date as YYYY-MM-DD."
            if invoice_date not in re.findall(r"\b\d{4}-\d{2}-\d{2}\b", user_message):
                return None, "I won't add a date that wasn't stated. Please include it as YYYY-MM-DD."
            values["invoice_date"] = invoice_date

        odoo_lines = []
        for line in lines:
            if not isinstance(line, dict):
                return None, "Please provide each product and quantity in a separate line."
            product = line.get("product_name")
            quantity = line.get("quantity")
            if not isinstance(product, str) or not product.strip():
                return None, "Which product should I include?"
            if isinstance(quantity, bool) or not isinstance(quantity, (int, float)) or quantity <= 0:
                return None, f"How many {product.strip()} should I include?"
            odoo_lines.append({"product_id": product.strip(), "quantity": quantity})

        if name == "create_invoice":
            model = "account.move"
            values["move_type"] = "out_invoice"
            values["invoice_line_ids"] = [[0, 0, line] for line in odoo_lines]
        else:
            model = "sale.order"
            values["order_line"] = [[0, 0, {
                "product_id": line["product_id"],
                "product_uom_qty": line["quantity"],
            }] for line in odoo_lines]
        return "odoo_create", {"model": model, "values": values}

    def _summarize_result(self, model: str, result: object) -> str:
        if isinstance(result, dict) and result.get("error"):
            return f"I couldn't complete the request: {result['error']}"
        if isinstance(result, dict) and result.get("status") == "success":
            label = "draft invoice" if model == "account.move" else "draft sales order"
            record_id = result.get("created_id")
            return f"Created a {label} in Odoo" + (f" (record {record_id})." if record_id else ".")
        if isinstance(result, dict) and result.get("status") == "cancelled":
            return "No draft was created because you declined the request."
        if isinstance(result, dict) and result.get("status") == "expired":
            return "The approval expired. Nothing was created."
        if isinstance(result, list):
            return f"Odoo returned {len(result)} matching record(s)."
        return "Odoo completed the request."

    def chat_stream(self, conv_id: str, user_message: str):
        history = self.get_or_create_history(conv_id)
        history.append({'role': 'user', 'content': user_message})
        model_name = os.getenv("OLLAMA_MODEL", "llama3.1")
        keep_alive = os.getenv("OLLAMA_KEEP_ALIVE", "").strip()
        total_started = time.perf_counter()
        model_ms = 0.0
        backend_ms = 0.0

        yield {"type": "status", "content": "Thinking..."}

        picked = self._take_choice(conv_id, user_message)
        choices = {}
        if picked:   # the user answered 'which one?': continue that request without asking the AI again
            picked_args, choices = picked
            tool_calls, direct_text = [_ToolCall("odoo_create", picked_args)], None
        else:
            call_options = {"model": model_name, "messages": history, "tools": TOOLS}
            if keep_alive:
                call_options["keep_alive"] = keep_alive
            model_started = time.perf_counter()
            try:
                response = ollama_chat(**call_options)
            except Exception:
                text = f"I couldn't reach the AI model '{model_name}'. Check that Ollama is running and the model is available."
                yield {"type": "token", "content": text}
                history.append({'role': 'assistant', 'content': text})
                total_ms = (time.perf_counter() - total_started) * 1000
                timings = {"model_ms": round(total_ms, 1), "backend_ms": 0, "total_ms": round(total_ms, 1)}
                self._audit("chat_timing", model=model_name, **timings)
                yield {"type": "metrics", "content": timings}
                yield {"type": "done", "content": ""}
                return
            model_ms = (time.perf_counter() - model_started) * 1000

            tool_calls = response.message.tool_calls or []
            direct_text = None
            if len(tool_calls) > 1:
                direct_text = "Please send one request at a time. Nothing was changed."
                tool_calls = []
            elif tool_calls:
                ai_call = tool_calls[0]
                tool_name, tool_args = self._map_intent(
                    ai_call.function.name, ai_call.function.arguments, user_message
                )
                if tool_name is None:
                    direct_text = tool_args
                    tool_calls = []
                else:
                    tool_calls = [_ToolCall(tool_name, tool_args)]

        if tool_calls:
            tool_model = tool_calls[0].function.arguments.get("model", "")
            backend_started = time.perf_counter()
            tool_result = None
            for tc in tool_calls:
                tool_name = tc.function.name
                tool_args = tc.function.arguments

                if tool_name == "odoo_create":
                    try:
                        raw_model = tool_args.get("model", "")
                        normalized = self.normalize_structure(tool_args.get("values", {}), raw_model)
                        resolved_values = self.resolve_entities(normalized, raw_model, choices)
                        tool_args["values"] = resolved_values
                    except ValueError as e:
                        if isinstance(e, AmbiguousName):
                            self.pending_choices[conv_id] = {"tool_args": copy.deepcopy(tool_args), "choices": choices,
                                                             "field": e.field, "raw": e.raw,
                                                             "candidates": e.candidates}
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

            backend_ms = (time.perf_counter() - backend_started) * 1000
            answer = self._summarize_result(tool_model, tool_result)
            yield {"type": "token", "content": answer}
            # This one-call flow doesn't send an assistant tool-call message. Drop the
            # tool responses so the next Ollama request won't see unmatched tool roles.
            while history and history[-1].get("role") == "tool":
                history.pop()
            history.append({'role': 'assistant', 'content': answer})
        else:
            text = direct_text or response.message.content or "Tell me what you would like to do in Odoo."
            yield {"type": "token", "content": text}
            history.append({'role': 'assistant', 'content': text})

        total_ms = (time.perf_counter() - total_started) * 1000
        timings = {
            "model_ms": round(model_ms, 1),
            "backend_ms": round(backend_ms, 1),
            "total_ms": round(total_ms, 1),
        }
        self._audit("chat_timing", model=model_name, **timings)
        yield {"type": "metrics", "content": timings}
        yield {"type": "done", "content": ""}
