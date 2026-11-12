"""
OdooClient - the only place where the app talks to Odoo.

The AI decides WHAT it wants; this file decides what is ALLOWED. These rules hold
no matter what the AI sends:

  * one XML-RPC connection per thread, with timeouts
        (one shared connection broke when two people used the app at once: 28 of 40 parallel requests failed)
  * short, clean error messages
        (Odoo returns a long traceback with server paths; that went to the AI and was hidden from the user)
  * read allow-list: only a few business models and fields, and a row limit
        (the AI could read any model, including system settings, and always fetched every record)
  * create allow-list: only DRAFT quotations and DRAFT customer invoices, only known fields
  * prices come from Odoo, not from the AI (unless ODOO_ALLOW_AI_PRICES=true)
        (an invoice was created at 10.00 while the product's price is 50.00)
  * every create - and every blocked attempt - is written to the audit log
"""
from __future__ import annotations

import ast
import http.client
import json
import logging
import re
import threading
import time
import urllib.request
import xmlrpc.client

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------
class OdooError(ValueError):
    """A short message that is safe to show to the user and the AI.

    `kind` says what went wrong: "not_allowed", "validation", "unreachable", "auth" or "odoo_error".
    It is a ValueError on purpose: the existing agent code already treats a ValueError
    as a normal "tool failed" result instead of crashing the chat.
    """

    def __init__(self, message: str, kind: str = "odoo_error"):
        super().__init__(message)
        self.kind = kind


class NotAllowedError(OdooError):
    def __init__(self, message: str):
        super().__init__(message, kind="not_allowed")


class OdooValidationError(OdooError):
    def __init__(self, message: str):
        super().__init__(message, kind="validation")


_ERROR_LINE = re.compile(r"^\s*((?:\w+\.)*\w*(?:Error|Exception|Warning)): (.*)$", re.MULTILINE)


def _from_fault(fault: xmlrpc.client.Fault) -> OdooError:
    """Turn Odoo's long traceback into one short line, without server paths."""
    text = str(fault.faultString or "")
    found = _ERROR_LINE.findall(text)
    if found:
        name, message = found[-1]
    else:
        lines = [l.strip() for l in text.splitlines() if l.strip()]
        name, message = "OdooError", (lines[-1] if lines else "unknown error")
    short_name = name.split(".")[-1]
    message = f"{short_name}: {message.strip()}"[:240]
    if short_name == "AccessError":
        return NotAllowedError(message)
    if short_name in ("ValidationError", "UserError", "ValueError", "MissingError", "KeyError"):
        return OdooValidationError(message)
    return OdooError(message)


# ---------------------------------------------------------------------------
# What may be read and created
# ---------------------------------------------------------------------------
READ_RULES = {
    "res.partner": {
        "fields": {"id", "name", "display_name", "email", "phone", "street", "zip", "city",
                   "country_id", "vat", "ref", "is_company", "customer_rank"},
        "default": ["id", "name", "email", "city"],
    },
    "product.product": {
        "fields": {"id", "name", "display_name", "default_code", "list_price", "type",
                   "uom_id", "sale_ok", "description_sale"},
        "default": ["id", "name", "list_price"],
    },
    "sale.order": {
        "fields": {"id", "name", "partner_id", "date_order", "state", "amount_untaxed",
                   "amount_tax", "amount_total", "invoice_status", "client_order_ref", "order_line"},
        "default": ["id", "name", "partner_id", "state", "amount_total"],
    },
    "account.move": {
        "fields": {"id", "name", "partner_id", "invoice_date", "invoice_date_due", "state",
                   "move_type", "payment_state", "amount_untaxed", "amount_tax", "amount_total",
                   "invoice_origin", "ref"},
        "default": ["id", "name", "partner_id", "state", "amount_total"],
        # customer invoices and credit notes only - no vendor bills or journal entries
        "forced_domain": [["move_type", "in", ["out_invoice", "out_refund"]]],
    },
}

CREATE_RULES = {
    "sale.order": {
        "fields": {"partner_id", "order_line", "client_order_ref", "note", "validity_date", "date_order"},
        "lines": "order_line",
        "qty": "product_uom_qty",
        "line_fields": {"product_id", "product_uom_qty", "name"},
    },
    "account.move": {
        "fields": {"partner_id", "move_type", "invoice_date", "invoice_date_due", "invoice_line_ids",
                   "ref", "narration", "invoice_origin"},
        "fixed": {"move_type": "out_invoice"},
        "lines": "invoice_line_ids",
        "qty": "quantity",
        "line_fields": {"product_id", "quantity", "name"},
    },
}
PRICE_FIELDS = {"price_unit", "discount"}


def _parse_list(value):
    """The AI sometimes sends a list as TEXT, e.g. "['name', 'email']". Turn it into a real list."""
    if isinstance(value, str):
        text = value.strip()
        for parser in (json.loads, ast.literal_eval):
            try:
                parsed = parser(text)
                if isinstance(parsed, (list, tuple)):
                    return list(parsed)
            except Exception:
                pass
        parts = [p.strip(" '\"") for p in text.strip("[]").split(",")]
        return [p for p in parts if p]
    return value


def _is_id(value) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value > 0


# ---------------------------------------------------------------------------
# Connection with timeouts
# ---------------------------------------------------------------------------
def _transport(url: str, timeout: float):
    base = xmlrpc.client.SafeTransport if url.startswith("https") else xmlrpc.client.Transport

    class _TimeoutTransport(base):
        def make_connection(self, host):
            conn = super().make_connection(host)
            conn.timeout = timeout
            return conn

    return _TimeoutTransport()


_NETWORK_ERRORS = (OSError, http.client.HTTPException, xmlrpc.client.ProtocolError)


class OdooClient:
    def __init__(self, url: str, db: str, username: str, password: str,
                 teams_webhook_url: str = "", *, timeout: float = 30.0, read_limit: int = 50,
                 allow_ai_prices: bool = False, audit=None, connect: bool = True):
        self.url = url.rstrip("/")
        self.db = db
        self.username = username
        self.password = password
        self.teams_webhook_url = teams_webhook_url or ""
        self.timeout = float(timeout)
        self.read_limit = int(read_limit)
        self.max_read_limit = max(self.read_limit, 200)
        self.allow_ai_prices = bool(allow_ai_prices)
        self.audit = audit
        self.uid = None
        self._local = threading.local()          # one XML-RPC connection per thread
        self._fields_cache: dict[str, set] = {}
        self._fields_lock = threading.Lock()
        if connect:                                 # connect=False is only used by offline unit tests
            self._authenticate()

    # -- connection ---------------------------------------------------------
    def _proxy(self, service: str):
        proxy = getattr(self._local, service, None)
        if proxy is None:
            proxy = xmlrpc.client.ServerProxy(f"{self.url}/xmlrpc/2/{service}",
                                              transport=_transport(self.url, self.timeout))
            setattr(self._local, service, proxy)
        return proxy

    def _drop_proxy(self, service: str):
        setattr(self._local, service, None)

    def _unreachable(self, exc) -> OdooError:
        if isinstance(exc, TimeoutError):
            return OdooError(f"Odoo did not answer within {self.timeout:.0f} seconds", kind="unreachable")
        return OdooError(f"Odoo is not reachable at {self.url} ({type(exc).__name__})", kind="unreachable")

    def _authenticate(self):
        try:
            self.uid = self._proxy("common").authenticate(self.db, self.username, self.password, {})
        except xmlrpc.client.Fault as f:
            raise _from_fault(f) from None
        except _NETWORK_ERRORS as e:
            self._drop_proxy("common")
            raise self._unreachable(e) from None
        if not self.uid:
            raise OdooError(f"Odoo login failed for user '{self.username}' on database '{self.db}'", kind="auth")

    def version(self) -> str:
        """Odoo's version string; also a cheap 'is Odoo up?' check."""
        try:
            return self._proxy("common").version()["server_version"]
        except _NETWORK_ERRORS as e:
            self._drop_proxy("common")
            raise self._unreachable(e) from None

    def _execute(self, model: str, method: str, args: list, kwargs: dict | None = None, *, retry: bool = False):
        attempts = 2 if retry else 1               # only reads are retried - never a create
        for attempt in range(attempts):
            try:
                return self._proxy("object").execute_kw(self.db, self.uid, self.password,
                                                        model, method, args, kwargs or {})
            except xmlrpc.client.Fault as f:
                raise _from_fault(f) from None
            except _NETWORK_ERRORS as e:
                self._drop_proxy("object")
                if attempt + 1 < attempts:
                    time.sleep(0.3)
                    continue
                raise self._unreachable(e) from None

    def _audit(self, event: str, **data):
        if self.audit is not None:
            self.audit.write(event, **data)

    # -- reading ------------------------------------------------------------
    def _existing_fields(self, model: str) -> set:
        with self._fields_lock:
            cached = self._fields_cache.get(model)
        if cached is not None:
            return cached
        try:
            names = set(self._execute(model, "fields_get", [], {"attributes": ["type"]}, retry=True))
        except OdooError:
            names = set(READ_RULES.get(model, {}).get("fields", set()))
        with self._fields_lock:
            self._fields_cache[model] = names
        return names

    def _check_domain(self, model: str, domain, allowed: set) -> list:
        domain = _parse_list(domain)
        if domain in (None, "", [], [[]]):
            domain = []
        if not isinstance(domain, (list, tuple)):
            raise OdooValidationError("The search filter must be a list like [['name', 'ilike', 'Pepsi']].")
        checked = []
        for term in domain:
            if term in ("&", "|", "!"):
                checked.append(term)
            elif isinstance(term, (list, tuple)) and len(term) == 0:
                continue
            elif isinstance(term, (list, tuple)) and len(term) == 3 and isinstance(term[0], str):
                if term[0].split(".")[0] not in allowed:
                    self._audit("read_blocked", model=model, reason=f"filter on '{term[0]}'")
                    raise NotAllowedError(f"Filtering on '{term[0]}' is not allowed for {model}.")
                checked.append(list(term))
            else:
                raise OdooValidationError(f"Invalid search filter term: {term!r}")
        return list(READ_RULES[model].get("forced_domain", [])) + checked

    def search_read(self, model: str, domain, fields, limit: int | None = None, order: str | None = None) -> list:
        rules = READ_RULES.get(model)
        if rules is None:
            self._audit("read_blocked", model=model, reason="model not allowed")
            raise NotAllowedError(f"Reading '{model}' is not allowed. Allowed: {', '.join(sorted(READ_RULES))}.")
        allowed = rules["fields"] & (self._existing_fields(model) | {"id"})
        requested = [f for f in (_parse_list(fields) or []) if isinstance(f, str)]
        chosen = [f for f in requested if f in allowed]
        if not chosen:
            chosen = [f for f in rules["default"] if f in allowed]
        dropped = sorted(set(requested) - set(chosen) - {"*"})
        if dropped:
            log.info("search_read %s: ignored fields %s", model, dropped)
        clean_domain = self._check_domain(model, domain, allowed)
        try:
            limit = min(int(limit), self.max_read_limit) if limit else self.read_limit
        except (TypeError, ValueError):
            limit = self.read_limit
        kwargs = {"fields": chosen, "limit": limit}
        if order and isinstance(order, str):
            kwargs["order"] = order
        return self._execute(model, "search_read", [clean_domain], kwargs, retry=True)

    # -- creating -----------------------------------------------------------
    def _guard_create(self, model: str, values: dict):
        rules = CREATE_RULES[model]
        values = dict(values or {})
        ignored = []
        for key, wanted in rules.get("fixed", {}).items():
            if key in values and values[key] != wanted:
                raise NotAllowedError(f"Only '{wanted}' records can be created here (got {key}={values[key]!r}).")
            values[key] = wanted

        clean = {}
        for key, value in values.items():
            if value is None:
                continue
            if key in rules["fields"]:
                clean[key] = value
            else:
                ignored.append(key)

        if not _is_id(clean.get("partner_id")):
            raise OdooValidationError("A known customer is required (the customer name must match a customer in Odoo).")

        lines = clean.get(rules["lines"])
        if not isinstance(lines, list) or not lines:
            raise OdooValidationError("At least one product line is required.")

        line_fields = rules["line_fields"] | (PRICE_FIELDS if self.allow_ai_prices else set())
        clean_lines = []
        for i, command in enumerate(lines, 1):
            if not (isinstance(command, (list, tuple)) and len(command) == 3
                    and command[0] == 0 and isinstance(command[2], dict)):
                raise NotAllowedError(f"Line {i}: only new lines can be added.")
            data = {}
            for key, value in command[2].items():
                if value is None:
                    continue
                if key in line_fields:
                    data[key] = value
                else:
                    ignored.append(f"line {i}: {key}")
            if not _is_id(data.get("product_id")):
                raise OdooValidationError(f"Line {i}: a known product is required.")
            qty_field = rules["qty"]
            try:
                qty = float(data.get(qty_field))
            except (TypeError, ValueError):
                raise OdooValidationError(f"Line {i}: a quantity is required.") from None
            if qty <= 0:
                raise OdooValidationError(f"Line {i}: quantity must be more than 0 (got {qty:g}).")
            data[qty_field] = qty
            clean_lines.append([0, 0, data])
        clean[rules["lines"]] = clean_lines
        return clean, ignored

    def create(self, model: str, values: dict) -> dict:
        if model not in CREATE_RULES:
            self._audit("create_blocked", model=model, reason="model not allowed")
            raise NotAllowedError(f"Creating '{model}' records is not allowed. "
                                  f"Allowed: draft quotations (sale.order) and draft customer invoices (account.move).")
        corrected = self._apply_auto_corrections(model, values)
        try:
            clean, ignored = self._guard_create(model, corrected)
        except OdooError as e:
            self._audit("create_blocked", model=model, reason=str(e))
            raise
        try:
            new_id = self._execute(model, "create", [clean])
        except OdooError as e:
            self._audit("create_failed", model=model, values=clean, error=str(e))
            raise
        self._audit("created", model=model, odoo_id=new_id, values=clean, ignored=ignored)
        self._notify_async(f"ERP Record Created: {model}",
                           f"Successfully generated a new entry under **{model}** with Database ID: `{new_id}`.")
        result = {"status": "success", "created_id": new_id, "state": "draft"}
        if ignored:
            result["ignored_fields"] = ignored
            if any(f.endswith(("price_unit", "discount")) for f in ignored):
                result["note"] = "Prices were taken from Odoo, not from the request."
        return result

    def _apply_auto_corrections(self, model: str, values: dict) -> dict:
        values = dict(values or {})
        if model == 'sale.order' and 'order_line' in values:
            raw_lines = values['order_line']
            if raw_lines and isinstance(raw_lines, list):
                for line in raw_lines:
                    if isinstance(line, list) and len(line) == 3 and isinstance(line[2], dict):
                        line_data = line[2]
                        if 'quantity' in line_data:
                            line_data['product_uom_qty'] = line_data.pop('quantity')

        if model == 'account.move' and 'invoice_line_ids' in values:
            raw_lines = values['invoice_line_ids']
            if raw_lines and isinstance(raw_lines, list):
                if not isinstance(raw_lines[0], list):
                    values['invoice_line_ids'] = [[0, 0, line] if isinstance(line, dict) else line for line in raw_lines]
                for line in values['invoice_line_ids']:
                    if isinstance(line, list) and len(line) == 3 and isinstance(line[2], dict):
                        line_data = line[2]
                        if 'product_uom_qty' in line_data:
                            line_data['quantity'] = line_data.pop('product_uom_qty')
        return values

    # -- Microsoft Teams (optional) ------------------------------------------
    def _notify_async(self, title: str, message: str, is_success: bool = True):
        url = self.teams_webhook_url
        if not url.startswith("https://") or "your-webhook-url" in url:
            return                                  # not configured (or still the template placeholder)
        threading.Thread(target=self.send_teams_notification, args=(title, message, is_success),
                         daemon=True).start()

    def send_teams_notification(self, title: str, message: str, is_success: bool = True):
        status_color = "Good" if is_success else "Attention"
        status_label = "SUCCESS" if is_success else "ERROR"
        payload = {
            "type": "message",
            "attachments": [{
                "contentType": "application/vnd.microsoft.card.adaptive",
                "content": {
                    "type": "AdaptiveCard",
                    "body": [{
                        "type": "Container",
                        "items": [
                            {"type": "TextBlock", "size": "Medium", "weight": "Bolder", "text": f"Odoo Agent Alert: {title}"},
                            {"type": "TextBlock", "text": f"Status: **{status_label}**", "color": status_color, "weight": "Bolder", "spacing": "Small"},
                            {"type": "TextBlock", "text": message, "wrap": True, "spacing": "Medium"}
                        ]
                    }],
                    "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
                    "version": "1.4"
                }
            }]
        }
        try:
            req = urllib.request.Request(
                self.teams_webhook_url,
                data=json.dumps(payload).encode('utf-8'),
                headers={'Content-Type': 'application/json'}
            )
            with urllib.request.urlopen(req, timeout=5):
                pass
        except Exception as e:                      # never let a notification break the app
            log.warning("Teams notification failed: %s", type(e).__name__)
