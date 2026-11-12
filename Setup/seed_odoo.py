#!/usr/bin/env python3
"""
seed_odoo.py - put reproducible TEST data into a fresh Odoo (Community 19/20).

What it does (safe to run more than once - it never creates the same record twice):
  1. Creates ~14 test customers, including deliberately confusing names
     ("Pepsi" / "Pepsi Cola Bottling", "Jansen Bouw" / "Jansen & Zonen") so we can test ambiguity handling.
  2. Creates ~14 test products with fixed prices (near-duplicates like "Chair" / "Chair Floor Protection" / "Ergonomic Chair").
  3. (optional) --create-agent-user: creates a dedicated low-privilege Odoo user for the AI app,
     instead of letting the AI run as the administrator.

Only needs Python 3 (standard library). Works on Windows, Mac, Linux.

Usage (PowerShell or terminal):
  python seed_odoo.py --db odoo --user you@example.com --password "your-odoo-password"
  python seed_odoo.py --db odoo --user you@example.com --password "..." --create-agent-user --agent-password "choose-one"
  python seed_odoo.py ... --check        # only print what exists, change nothing

Settings can also come from environment variables ODOO_URL, ODOO_DB, ODOO_USER, ODOO_PASS
or from a .env file (see --env-file).
"""
import argparse
import os
import sys
import xmlrpc.client

CUSTOMERS = [
    # (name, city, email)  - near-duplicates on purpose
    ("Pepsi", "Rotterdam", "orders@pepsi.example"),
    ("Pepsi Cola Bottling", "Utrecht", "info@pepsicola.example"),
    ("L. Luther", "Arnhem", "l.luther@example.com"),
    ("Jansen Bouw", "Nijmegen", "info@jansenbouw.example"),
    ("Jansen & Zonen", "Eindhoven", "info@jansenzonen.example"),
    ("De Vries Fietsen", "Zwolle", "winkel@devriesfietsen.example"),
    ("Van den Berg Catering", "Amersfoort", "info@vandenberg.example"),
    ("Bakkerij Smit", "Ede", "bakker@smit.example"),
    ("Tech4Kids", "Delft", "hello@tech4kids.example"),
    ("Nordic Furniture GmbH", "Hamburg", "sales@nordic.example"),
    ("Müller GmbH", "Köln", "einkauf@mueller.example"),
    ("Acme BV", "Amsterdam", "inkoop@acme.example"),
    ("Acme Trading BV", "Den Haag", "trade@acmetrading.example"),
    ("Studio Lux", "Haarlem", "studio@lux.example"),
]

PRODUCTS = [
    # (name, sales price, type)  type: 'consu' = goods, 'service' = service
    ("Chair", 50.00, "consu"),
    ("Chair Floor Protection", 12.50, "consu"),
    ("Ergonomic Chair", 220.00, "consu"),
    ("Desk", 200.00, "consu"),
    ("Desk Lamp", 25.00, "consu"),
    ("Standing Desk", 480.00, "consu"),
    ("Office Desk Large", 350.00, "consu"),
    ("Monitor Stand", 45.00, "consu"),
    ("Whiteboard", 80.00, "consu"),
    ("Filing Cabinet", 120.00, "consu"),
    ("Keyboard", 35.00, "consu"),
    ("Cable Management Kit", 9.90, "consu"),
    ("Installation Service", 90.00, "service"),
    ("Delivery", 15.00, "service"),
]


def load_env_file(path):
    vals = {}
    if path and os.path.exists(path):
        for line in open(path, encoding="utf-8"):
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                vals[k.strip()] = v.split("#")[0].strip()
    return vals


class Odoo:
    def __init__(self, url, db, user, password):
        self.url, self.db, self.password = url.rstrip("/"), db, password
        common = xmlrpc.client.ServerProxy(f"{self.url}/xmlrpc/2/common")
        self.version = common.version()["server_version"]
        self.uid = common.authenticate(db, user, password, {})
        if not self.uid:
            sys.exit(f"Login failed for '{user}' on database '{db}'. Check --db / --user / --password.")
        self.models = xmlrpc.client.ServerProxy(f"{self.url}/xmlrpc/2/object")

    def call(self, model, method, *args, **kw):
        return self.models.execute_kw(self.db, self.uid, self.password, model, method, list(args), kw)

    def find(self, model, domain):
        ids = self.call(model, "search", domain, limit=1)
        return ids[0] if ids else None


def seed_customers(o, check):
    created = existing = 0
    for name, city, email in CUSTOMERS:
        if o.find("res.partner", [("name", "=", name)]):
            existing += 1
            continue
        if not check:
            o.call("res.partner", "create", {"name": name, "city": city, "email": email,
                                              "is_company": True, "customer_rank": 1})
        created += 1
    return created, existing


def seed_products(o, check):
    created = existing = 0
    for name, price, ptype in PRODUCTS:
        if o.find("product.product", [("name", "=", name)]):
            existing += 1
            continue
        if not check:
            o.call("product.product", "create", {"name": name, "list_price": price, "type": ptype,
                                                  "sale_ok": True})
        created += 1
    return created, existing


def create_agent_user(o, login, password, check):
    """Dedicated user for the AI app: can create quotations/invoices, but is NOT an administrator."""
    if o.find("res.users", [("login", "=", login)]):
        return "already exists"
    if check:
        return "would be created"
    # the field that holds a user's groups was renamed in Odoo 19 (groups_id -> group_ids)
    fields = o.call("res.users", "fields_get", attributes=["type"])
    gfield = "group_ids" if "group_ids" in fields else "groups_id"
    groups = []
    for xmlid in ("sales_team.group_sale_salesman_all_leads", "account.group_account_invoice"):
        module, name = xmlid.split(".")
        rec = o.call("ir.model.data", "search_read", [("module", "=", module), ("name", "=", name)],
                     fields=["res_id"], limit=1)
        if not rec:
            sys.exit(f"Could not find group {xmlid}. Are Sales and Invoicing installed?")
        groups.append((4, rec[0]["res_id"]))
    o.call("res.users", "create", {"name": "AI Agent", "login": login, "password": password,
                                    gfield: groups})
    return "created"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--env-file", default=".env", help="optional .env file with ODOO_URL/ODOO_DB/ODOO_USER/ODOO_PASS")
    ap.add_argument("--url"), ap.add_argument("--db"), ap.add_argument("--user"), ap.add_argument("--password")
    ap.add_argument("--create-agent-user", action="store_true")
    ap.add_argument("--agent-login", default="ai_agent")
    ap.add_argument("--agent-password", default=None)
    ap.add_argument("--check", action="store_true", help="dry run: show what would be created")
    a = ap.parse_args()

    env = {**load_env_file(a.env_file), **{k: v for k, v in os.environ.items() if k.startswith("ODOO_")}}
    url = a.url or env.get("ODOO_URL", "http://127.0.0.1:8069")
    db = a.db or env.get("ODOO_DB", "odoo")
    user = a.user or env.get("ODOO_USER")
    pw = a.password or env.get("ODOO_PASS")
    if not user or not pw:
        sys.exit("Need --user and --password (or ODOO_USER / ODOO_PASS).")

    o = Odoo(url, db, user, pw)
    print(f"Connected to Odoo {o.version} (db '{db}') as uid {o.uid}")
    print("MODE:", "CHECK ONLY (nothing is written)" if a.check else "WRITE")

    c, ce = seed_customers(o, a.check)
    print(f"Customers: {'would create' if a.check else 'created'} {c}, already there {ce}")
    p, pe = seed_products(o, a.check)
    print(f"Products : {'would create' if a.check else 'created'} {p}, already there {pe}")

    if a.create_agent_user:
        if not a.agent_password:
            sys.exit("--create-agent-user needs --agent-password")
        print(f"Agent user '{a.agent_login}':", create_agent_user(o, a.agent_login, a.agent_password, a.check))

    print("Done. Next: put the login you want the AI to use into Application/V3.1/.env")


if __name__ == "__main__":
    main()
