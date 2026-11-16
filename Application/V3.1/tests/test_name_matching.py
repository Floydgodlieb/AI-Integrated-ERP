"""Customer/product names -> Odoo ids: exact name wins, one partial match is used, several matches -> ask."""
import pytest

from backend.agent import ConversationAgent


class StubOdoo:
    """Answers name searches like Odoo would, from a fixed list."""
    names = {"res.partner": ["Pepsi", "Pepsi Cola Bottling", "Jansen Bouw", "Jansen & Zonen"]}

    def search_read(self, model, domain, fields):
        _, op, text = domain[0]
        hit = (lambda n: n.lower() == text.lower()) if op == "=ilike" else (lambda n: text.lower() in n.lower())
        return [{"id": i, "name": n} for i, n in enumerate(self.names.get(model, []), 1) if hit(n)]


def resolve(odoo, **values):
    return ConversationAgent(odoo).resolve_entities(values)


def test_offline_rules():
    assert resolve(StubOdoo(), partner_id="pepsi")["_resolved_partner_id_name"] == "Pepsi"
    with pytest.raises(ValueError, match="More than one customer matches 'Jansen': Jansen Bouw, Jansen & Zonen"):
        resolve(StubOdoo(), partner_id="Jansen")
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
