"""Tests against a real Odoo (skipped when Odoo is not running). Needs the seed data from Setup/seed_odoo.py."""
import threading
from collections import Counter

import pytest

from backend.odoo_client import NotAllowedError, OdooError


def test_forty_parallel_reads_all_succeed(odoo):
    # Before: one shared connection -> 28 of 40 parallel requests failed.
    results = []

    def read():
        try:
            rows = odoo.search_read("res.partner", [], ["name"])
            results.append("ok" if rows else "empty")
        except Exception as e:                       # pragma: no cover - this is what we test against
            results.append(type(e).__name__)

    threads = [threading.Thread(target=read) for _ in range(40)]
    [t.start() for t in threads]
    [t.join() for t in threads]
    assert Counter(results) == Counter({"ok": 40})


def test_seed_data_is_present(odoo):
    names = {r["name"] for r in odoo.search_read("res.partner", [["customer_rank", ">", 0]], ["name"])}
    assert {"Pepsi", "Pepsi Cola Bottling", "Jansen Bouw", "L. Luther"} <= names


def test_fields_sent_as_text_still_work(odoo):
    # Floyd's real failure: Odoo answered "Invalid field '['" because fields arrived as text.
    rows = odoo.search_read("res.partner", "[]", "['name', 'email', 'phone']")
    assert rows and {"name", "email", "phone"} <= set(rows[0])


def test_unknown_or_forbidden_fields_are_left_out(odoo):
    rows = odoo.search_read("res.partner", [], ["name", "does_not_exist", "password"])
    assert rows and set(rows[0]) == {"id", "name"}


def test_filtering_on_a_forbidden_field_is_blocked(odoo):
    with pytest.raises(NotAllowedError):
        odoo.search_read("res.partner", [["user_ids.login", "=", "admin"]], ["name"])


def test_reads_are_limited(odoo):
    assert len(odoo.search_read("res.partner", [], ["name"], limit=3)) <= 3
    assert len(odoo.search_read("res.partner", [], ["name"])) <= odoo.read_limit


def test_odoo_errors_are_short(odoo):
    with pytest.raises(OdooError) as info:
        odoo.search_read("res.partner", [["name", "not-an-operator", "x"]], ["name"])
    message = str(info.value)
    assert "Traceback" not in message and "/" not in message.split(":")[0]
    assert len(message) <= 240


def _product(odoo, name):
    return odoo.search_read("product.product", [["name", "=", name]], ["id", "list_price"])[0]


def _customer(odoo, name):
    return odoo.search_read("res.partner", [["name", "=", name]], ["id"])[0]["id"]


def test_invoice_uses_odoo_price_not_ai_price(odoo, audit):
    chair = _product(odoo, "Chair")
    result = odoo.create("account.move", {
        "partner_id": _customer(odoo, "Pepsi"), "move_type": "out_invoice", "ref": "pytest",
        "invoice_line_ids": [[0, 0, {"product_id": chair["id"], "quantity": 3, "price_unit": 10.0}]]})
    assert result["status"] == "success" and result["state"] == "draft"
    assert "line 1: price_unit" in result["ignored_fields"]
    invoice = odoo._execute("account.move", "read", [[result["created_id"]]],
                            {"fields": ["state", "amount_untaxed", "invoice_line_ids"]})[0]
    assert invoice["state"] == "draft"
    assert invoice["amount_untaxed"] == pytest.approx(3 * chair["list_price"])
    assert audit.read_all()[-1]["event"] == "created"


def test_sales_order_is_created_as_draft(odoo):
    result = odoo.create("sale.order", {
        "partner_id": _customer(odoo, "Pepsi"), "client_order_ref": "pytest", "state": "sale",
        "order_line": [[0, 0, {"product_id": _product(odoo, "Desk")["id"], "product_uom_qty": 2}]]})
    order = odoo._execute("sale.order", "read", [[result["created_id"]]], {"fields": ["state", "amount_untaxed"]})[0]
    assert order["state"] == "draft"                 # the AI's "state": "sale" was ignored
    assert order["amount_untaxed"] == pytest.approx(2 * _product(odoo, "Desk")["list_price"])
