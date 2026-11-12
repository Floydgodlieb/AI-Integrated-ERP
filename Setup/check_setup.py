#!/usr/bin/env python3
"""
check_setup.py - one command that tells you whether the whole chain is ready.
Read-only: it does NOT create or change anything.

  python check_setup.py                       # reads ODOO_* from Application/V3/.env or ./.env
  python check_setup.py --env-file Application/V3/.env

Checks: Odoo reachable + version, login as the AI user, Sales/Invoicing installed,
seed data present, the AI user is NOT an admin (cannot read system settings),
Ollama running + model pulled, V3 backend health.
"""
import argparse, json, os, sys, urllib.request, xmlrpc.client

OK, BAD, WARN = "[ OK ]", "[FAIL]", "[WARN]"
fails = 0


def line(tag, msg):
    global fails
    if tag == BAD:
        fails += 1
    print(f"{tag} {msg}")


def load_env(path):
    vals = {}
    if path and os.path.exists(path):
        for l in open(path, encoding="utf-8"):
            l = l.strip()
            if l and not l.startswith("#") and "=" in l:
                k, v = l.split("=", 1)
                vals[k.strip()] = v.split("#")[0].strip()
    return vals


def http_json(url, timeout=5):
    with urllib.request.urlopen(url, timeout=timeout) as r:
        return json.loads(r.read().decode())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--env-file", default=None)
    ap.add_argument("--ollama-url", default=os.environ.get("OLLAMA_HOST", "http://localhost:11434"))
    ap.add_argument("--backend-url", default="http://localhost:8001")
    ap.add_argument("--model", default="llama3.1")
    a = ap.parse_args()

    env_path = a.env_file or next((p for p in ("Application/V3/.env", ".env", "../.env") if os.path.exists(p)), None)
    env = {**load_env(env_path), **{k: v for k, v in os.environ.items() if k.startswith("ODOO_")}}
    print(f"Using settings from: {env_path or '(environment only)'}\n")
    url, db = env.get("ODOO_URL", "http://localhost:8069"), env.get("ODOO_DB", "odoo")
    user, pw = env.get("ODOO_USER"), env.get("ODOO_PASS")

    # 1. Odoo reachable
    try:
        ver = xmlrpc.client.ServerProxy(f"{url}/xmlrpc/2/common").version()
        line(OK, f"Odoo reachable at {url} - version {ver['server_version']}")
    except Exception as e:
        line(BAD, f"Odoo not reachable at {url}: {e}"); return finish()

    # 2. login
    if not user or not pw:
        line(BAD, "ODOO_USER / ODOO_PASS missing in .env"); return finish()
    common = xmlrpc.client.ServerProxy(f"{url}/xmlrpc/2/common")
    uid = common.authenticate(db, user, pw, {})
    if not uid:
        line(BAD, f"Login failed for '{user}' on database '{db}'"); return finish()
    line(OK, f"Logged in as '{user}' (uid {uid}) on database '{db}'")
    m = xmlrpc.client.ServerProxy(f"{url}/xmlrpc/2/object")

    def call(model, method, *args, **kw):
        return m.execute_kw(db, uid, pw, model, method, list(args), kw)

    # 3. modules
    try:
        mods = {r["name"]: r["state"] for r in call("ir.module.module", "search_read",
                [("name", "in", ["sale_management", "sale", "account"])], fields=["name", "state"])}
        line(OK if all(mods.get(x) == "installed" for x in ("sale", "account")) else BAD,
             f"Apps: {mods or 'could not read module list (user may lack rights - that is fine)'}")
    except Exception:
        line(WARN, "Could not read module list with this user (normal for a limited user). Checking via records instead.")

    # 4. seed data
    try:
        cust = call("res.partner", "search_count", [("customer_rank", ">", 0)])
        prods = call("product.product", "search_count", [("sale_ok", "=", True)])
        line(OK if cust >= 10 else WARN, f"Customers with customer_rank>0: {cust} (seed script creates 14)")
        line(OK if prods >= 10 else WARN, f"Sellable products: {prods} (seed script creates 14)")
    except Exception as e:
        line(BAD, f"Could not read customers/products: {str(e)[:120]}")

    # 5. least privilege
    try:
        call("ir.config_parameter", "search_read", [], fields=["key"], limit=1)
        line(WARN, "This user CAN read system settings (ir.config_parameter) - it looks like an administrator. "
                   "Use the dedicated agent user (seed_odoo.py --create-agent-user).")
    except Exception:
        line(OK, "This user cannot read system settings (limited user - good)")

    # 6. Ollama
    try:
        tags = http_json(a.ollama_url.rstrip("/") + "/api/tags")
        names = [t["name"] for t in tags.get("models", [])]
        has = any(n.split(":")[0] == a.model.split(":")[0] for n in names)
        line(OK if has else BAD, f"Ollama running; models: {names or 'none'}" + ("" if has else f"  -> run: ollama pull {a.model}"))
    except Exception as e:
        line(BAD, f"Ollama not reachable at {a.ollama_url} ({e}). Install from ollama.com and start it.")

    # 7. backend
    try:
        h = http_json(a.backend_url.rstrip("/") + "/api/health")
        line(OK if h.get("status") == "ok" else BAD, f"V3 backend health: {h}")
    except Exception:
        line(WARN, f"V3 backend not running at {a.backend_url} (start it, then run this again)")
    finish()


def finish():
    print("\n" + ("ALL REQUIRED CHECKS PASSED" if fails == 0 else f"{fails} CHECK(S) FAILED - fix the [FAIL] lines above"))
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
