"""Customer/product names -> Odoo ids (backend side; the AI only sends names and quantities)."""

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


class AmbiguousName(ValueError):
    """Several Odoo records match a name; the user picks one in the next message."""

    def __init__(self, field: str, raw: str, label: str, candidates: list, intro: str = ""):
        self.field, self.raw, self.candidates = field, raw, candidates
        options = "\n".join(f"{i}. {c['name']}" for i, c in enumerate(candidates, 1))
        intro = intro or f"More than one {label} matches '{raw}':"
        super().__init__(f"{intro}\n{options}\nReply with the number or the full name.")


def normalize_structure(values: dict, model: str) -> dict:
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

def resolve_entities(odoo, values: dict, model: str = None, choices: dict | None = None, suggest=None) -> dict:
    """`suggest(text, names) -> name | None` (optional): an AI guess for a product name that matches nothing."""
    resolved = {}
    for field, raw_value in values.items():
        if field in NESTED_LINE_FIELDS and isinstance(raw_value, list):
            resolved_lines = []
            for item in raw_value:
                if isinstance(item, list) and len(item) == 3:
                    resolved_lines.append([item[0], item[1], resolve_entities(odoo, item[2], model, choices, suggest)])
                elif isinstance(item, dict):
                    resolved_lines.append(resolve_entities(odoo, item, model, choices, suggest))
                else:
                    resolved_lines.append(item)
            resolved[field] = resolved_lines
        elif field in FIELD_MODEL_MAP and isinstance(raw_value, str):
            search_model = FIELD_MODEL_MAP[field]
            # Exact name (any case) wins; else one partial match; several matches -> ask, never guess.
            # shortcut: % and _ in the name act as wildcards in =ilike, escape them if names ever contain them
            picked = (choices or {}).get((field, raw_value.strip().lower()))
            # never pick our own company or internal users (My Company, Administrator, AI Agent) as customer
            extra = [["id", "not in", odoo.internal_partner_ids()]] if search_model == "res.partner" else []
            def find(text):
                return (odoo.search_read(search_model, [["name", "=ilike", text]] + extra, ["name", "id"])
                        or odoo.search_read(search_model, [["name", "ilike", text]] + extra, ["name", "id"]))
            results = [picked] if picked else find(raw_value)
            # shortcut: only strips one trailing "s" (chairs -> chair); other plurals need the AI to send the singular
            if not results and raw_value.strip().lower().endswith("s"):
                results = find(raw_value.strip()[:-1])
            label = MODEL_LABELS.get(search_model, search_model).lower()
            if not results and suggest and search_model == "product.product":
                # shortcut: offers at most 200 sellable product names to the AI; a bigger catalogue needs a search step first
                products = odoo.search_read("product.product", [["sale_ok", "=", True]], ["id", "name"], limit=200)
                guess = suggest(raw_value, [p["name"] for p in products])
                match = next((p for p in products if p["name"] == guess), None)   # the check: must be a real product
                if match:   # never accepted silently: the user confirms by replying 1 or the name
                    raise AmbiguousName(field, raw_value, label, [match],
                                        intro=f"No product named '{raw_value}'. Did you mean:")
            if not results:
                raise ValueError(f"Could not find a {label} named '{raw_value}'.")
            if len(results) > 1:
                # shortcut: only the first 5 matches are offered; a longer list needs a search box in the chat
                raise AmbiguousName(field, raw_value, label, results[:5])
            resolved[field] = results[0]["id"]
            resolved[f"_resolved_{field}_name"] = results[0]["name"]
        else:
            resolved[field] = raw_value
    return resolved


def prepare_review(odoo, model: str, values: dict) -> dict:
    """What the approval card shows besides names: Odoo list price per line, total and duplicate warnings.

    Adds `_resolved_product_id_price` to each line (keys starting with "_" never reach Odoo) and returns
    {"total_untaxed": float, "warnings": [str]} for the card. Never uses a price sent by the AI.
    """
    lines = [cmd[2] for cmd in values.get("order_line") or values.get("invoice_line_ids") or []
             if isinstance(cmd, (list, tuple)) and len(cmd) == 3 and isinstance(cmd[2], dict)]
    ids = sorted({line["product_id"] for line in lines if isinstance(line.get("product_id"), int)})
    prices = {r["id"]: r["list_price"] for r in
              odoo.search_read("product.product", [["id", "in", ids]], ["id", "list_price"])} if ids else {}
    total = 0.0
    for line in lines:
        price = prices.get(line.get("product_id"), 0.0)
        line["_resolved_product_id_price"] = price
        total += price * float(line.get("quantity", line.get("product_uom_qty", 0)) or 0)
    total = round(total, 2)

    warnings = []
    partner = values.get("partner_id")
    if isinstance(partner, int):
        label = "draft invoice" if model == "account.move" else "quotation"
        for draft in odoo.recent_drafts(model, partner):
            if round(draft["amount_untaxed"], 2) == total:   # same customer and same amount in the last 24 h
                ref = draft["name"] if draft["name"] and draft["name"] != "/" else f"record {draft['id']}"
                warnings.append(f"Possible duplicate: {label} {ref} for this customer has the same amount "
                                f"({total:.2f}) and was created in the last 24 hours.")
                break
    return {"total_untaxed": total, "warnings": warnings}
