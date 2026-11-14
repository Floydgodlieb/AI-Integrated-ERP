"""Flat Ollama JSON schema used by the AI extraction replay."""

ACTION_NAMES = [
    "create_invoice",
    "create_sales_order",
    "lookup",
    "ask_clarification",
    "refuse",
]

AI_INTENT_SCHEMA = {
    "type": "object",
    "properties": {
        "schema_version": {"type": "string", "enum": ["0.1"]},
        "result": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ACTION_NAMES},
                "customer_name": {"type": ["string", "null"]},
                "lines": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "product_name": {"type": "string"},
                            "quantity": {"type": "number", "exclusiveMinimum": 0},
                        },
                        "required": ["product_name", "quantity"],
                        "additionalProperties": False,
                    },
                },
                "invoice_date": {"type": ["string", "null"], "format": "date"},
                "what": {
                    "type": ["string", "null"],
                    "enum": ["customers", "products", "sales_orders", "invoices", None],
                },
                "search_text": {"type": ["string", "null"]},
                "limit": {"type": "integer", "minimum": 1, "maximum": 50},
                "missing": {
                    "type": "array",
                    "items": {"type": "string", "enum": ["customer", "product", "quantity", "date", "other"]},
                },
                "question": {"type": ["string", "null"]},
                "reason": {"type": ["string", "null"]},
            },
            "required": ["action"],
            "additionalProperties": False,
        },
    },
    "required": ["schema_version", "result"],
    "additionalProperties": False,
}
