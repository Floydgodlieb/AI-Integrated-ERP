"""Customer/product names -> Odoo ids: exact name wins, one partial match is used, several matches -> ask."""
import pytest

from backend.agent import ConversationAgent


class StubOdoo:
    """Answers name searches like Odoo would, from a fixed list."""
    names = {"res.partner": ["Pepsi", "Pepsi Cola Bottling", "Jansen Bouw", "Jansen & Zonen"]}

    def internal_partner_ids(self):
        return []

    def search_read(self, model, domain, fields, limit=None):
        _, op, text = domain[0]
        hit = (lambda n: n.lower() == text.lower()) if op == "=ilike" else (lambda n: text.lower() in n.lower())
        return [{"id": i, "name": n} for i, n in enumerate(self.names.get(model, []), 1) if hit(n)]


def resolve(odoo, **values):
    return ConversationAgent(odoo).resolve_entities(values)


def test_offline_rules():
    assert resolve(StubOdoo(), partner_id="pepsi")["_resolved_partner_id_name"] == "Pepsi"
    with pytest.raises(ValueError, match="More than one customer matches 'Jansen':\n1. Jansen Bouw\n2. Jansen & Zonen"):
        resolve(StubOdoo(), partner_id="Jansen")
    picked = {("partner_id", "jansen"): {"id": 4, "name": "Jansen & Zonen"}}     # the user's answer "2"
    assert ConversationAgent(StubOdoo()).resolve_entities({"partner_id": "Jansen"}, choices=picked)["partner_id"] == 4
    with pytest.raises(ValueError, match="Could not find"):
        resolve(StubOdoo(), partner_id="Globex")


# --- against the seeded Odoo (skipped when Odoo is not running) ------------------
@pytest.mark.parametrize("field,text,expected", [
    ("partner_id", "Pepsi", "Pepsi"),                      # exact wins over "Pepsi Cola Bottling"
    ("partner_id", "pepsi", "Pepsi"),                      # any case
    ("product_id", "Chair", "Chair"),                      # not "Ergonomic Chair" / "Chair Floor Protection"
    ("product_id", "Floor", "Chair Floor Protection"),     # single partial match is used (card shows the full name)
])
def test_seed_data_resolves(odoo, field, text, expected):
    assert resolve(odoo, **{field: text})[f"_resolved_{field}_name"] == expected


@pytest.mark.parametrize("text", ["Jansen", "Acme", "pep"])
def test_seed_data_ambiguous_names_ask(odoo, text):
    with pytest.raises(ValueError, match="More than one customer"):
        resolve(odoo, partner_id=text)


def test_own_company_and_internal_users_are_never_customers(odoo):
    for name in ("My Company", "Administrator", "AI Agent"):
        with pytest.raises(ValueError, match="Could not find"):
            resolve(odoo, partner_id=name)


def test_review_uses_odoo_price_and_total(odoo):
    from backend import resolver
    values = resolve(odoo, partner_id="Pepsi", invoice_line_ids=[[0, 0, {"product_id": "Chair", "quantity": 3, "price_unit": 10.0}]])
    review = resolver.prepare_review(odoo, "account.move", values)
    assert values["invoice_line_ids"][0][2]["_resolved_product_id_price"] == 50.0      # Odoo price, not the AI's 10.00
    assert review["total_untaxed"] == 150.0


def test_failing_suggestion_call_means_plain_not_found(monkeypatch):
    from backend import agent as agent_module

    class BrokenClient:                     # e.g. the model is too slow and times out
        def __init__(self, **kw):
            pass

        def chat(self, **kw):
            raise TimeoutError("model too slow")

    monkeypatch.setattr(agent_module, "Client", BrokenClient)
    agent = ConversationAgent(StubOdoo())
    assert agent._suggest_product("premium chair", ["Chair", "Ergonomic Chair"]) is None
    with pytest.raises(ValueError, match="Could not find a customer named 'Globex'"):   # customers never get suggestions
        agent.resolve_entities({"partner_id": "Globex"})
