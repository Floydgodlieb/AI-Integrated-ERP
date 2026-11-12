"""Offline tests: the backend's safety rules, without Odoo running."""
import xmlrpc.client

import pytest

from backend.odoo_client import (NotAllowedError, OdooError, OdooValidationError, OdooClient,
                                 _from_fault, _parse_list)

# The exact error Odoo 20 sent on Floyd's Windows PC when the AI sent fields as text.
REAL_WINDOWS_TRACEBACK = (
    'Traceback (most recent call last):\n'
    '  File "C:\\Program Files\\Odoo 20.0.20261109\\server\\odoo\\orm\\models.py", line 3201, in _determine_fields_to_fetch\n'
    "    field = self._fields[field_name]\n"
    "KeyError: '['\n\n"
    "The above exception was the direct cause of the following exception:\n\n"
    'Traceback (most recent call last):\n'
    '  File "C:\\Program Files\\Odoo 20.0.20261109\\server\\odoo\\orm\\models.py", line 3203, in _determine_fields_to_fetch\n'
    "    raise ValueError(f\"Invalid field {field_name!r} on {self._name!r}\") from e\n"
    "ValueError: Invalid field '[' on 'res.partner'\n"
)


def invoice(**line):
    return {"partner_id": 6, "move_type": "out_invoice",
            "invoice_line_ids": [[0, 0, {"product_id": 1, "quantity": 3, **line}]]}


# --- error cleaning -----------------------------------------------------------
def test_odoo_traceback_becomes_one_short_line():
    err = _from_fault(xmlrpc.client.Fault(1, REAL_WINDOWS_TRACEBACK))
    assert str(err) == "ValueError: Invalid field '[' on 'res.partner'"
    assert "Program Files" not in str(err) and "Traceback" not in str(err)
    assert err.kind == "validation"


def test_access_error_is_reported_as_not_allowed():
    err = _from_fault(xmlrpc.client.Fault(2, "Traceback...\nodoo.exceptions.AccessError: You are not allowed\n"))
    assert isinstance(err, NotAllowedError) and str(err) == "AccessError: You are not allowed"


def test_errors_are_value_errors_so_the_agent_handles_them():
    assert issubclass(OdooError, ValueError)


# --- input cleaning -----------------------------------------------------------
@pytest.mark.parametrize("raw,expected", [
    ("['name', 'email', 'phone']", ["name", "email", "phone"]),   # what llama3.1 really sent
    ('["name", "id"]', ["name", "id"]),
    ("name, email", ["name", "email"]),
    (["name"], ["name"]),
])
def test_lists_sent_as_text_are_understood(raw, expected):
    assert _parse_list(raw) == expected


# --- create rules (no Odoo needed) ---------------------------------------------
def test_ai_price_is_ignored_and_odoo_price_used(offline_client):
    clean, ignored = offline_client._guard_create("account.move", invoice(price_unit=10.0))
    assert "price_unit" not in clean["invoice_line_ids"][0][2]
    assert "line 1: price_unit" in ignored


def test_ai_price_kept_only_when_explicitly_allowed(offline_client):
    offline_client.allow_ai_prices = True
    clean, _ = offline_client._guard_create("account.move", invoice(price_unit=10.0))
    assert clean["invoice_line_ids"][0][2]["price_unit"] == 10.0


def test_only_customer_invoices_can_be_created(offline_client):
    with pytest.raises(NotAllowedError):
        offline_client._guard_create("account.move", {**invoice(), "move_type": "in_invoice"})
    clean, _ = offline_client._guard_create("account.move", {k: v for k, v in invoice().items() if k != "move_type"})
    assert clean["move_type"] == "out_invoice"


@pytest.mark.parametrize("qty", [0, -2, "lots", None])
def test_bad_quantities_are_rejected(offline_client, qty):
    values = invoice()
    values["invoice_line_ids"][0][2]["quantity"] = qty
    with pytest.raises(OdooValidationError):
        offline_client._guard_create("account.move", values)


def test_customer_must_be_a_real_odoo_id(offline_client):
    with pytest.raises(OdooValidationError):
        offline_client._guard_create("account.move", {**invoice(), "partner_id": "Pepsi"})


def test_at_least_one_line_is_required(offline_client):
    with pytest.raises(OdooValidationError):
        offline_client._guard_create("sale.order", {"partner_id": 6, "order_line": []})


def test_only_new_lines_can_be_added(offline_client):
    with pytest.raises(NotAllowedError):
        offline_client._guard_create("sale.order", {"partner_id": 6, "order_line": [[6, 0, [1, 2]]]})


def test_unknown_fields_are_dropped_not_sent_to_odoo(offline_client):
    clean, ignored = offline_client._guard_create("sale.order", {
        "partner_id": 6, "state": "sale", "user_id": 1,
        "order_line": [[0, 0, {"product_id": 1, "product_uom_qty": 1, "tax_ids": [[6, 0, []]]}]]})
    assert "state" not in clean and "user_id" not in clean
    assert "tax_ids" not in clean["order_line"][0][2]
    assert {"state", "user_id", "line 1: tax_ids"} <= set(ignored)


def test_other_models_cannot_be_created(offline_client, audit):
    with pytest.raises(NotAllowedError):
        offline_client.create("res.partner", {"name": "New customer"})
    assert audit.read_all()[-1]["event"] == "create_blocked"


def test_other_models_cannot_be_read(offline_client, audit):
    for model in ("res.users", "ir.config_parameter", "account.account"):
        with pytest.raises(NotAllowedError):
            offline_client.search_read(model, [], ["name"])
    assert [r["event"] for r in audit.read_all()] == ["read_blocked"] * 3


def test_localhost_is_replaced_by_ipv4():
    # Measured on Windows: localhost 2.08 s per new connection, 127.0.0.1 0.03 s.
    client = OdooClient("http://localhost:8069/", "odoo", "u", "p", connect=False)
    assert client.url == "http://127.0.0.1:8069"
    assert OdooClient("https://odoo.example.com", "odoo", "u", "p", connect=False).url == "https://odoo.example.com"


def test_unreachable_odoo_gives_a_clear_error():
    with pytest.raises(OdooError) as info:
        OdooClient("http://127.0.0.1:9", "odoo", "ai_agent", "x", timeout=3)
    assert info.value.kind == "unreachable"
