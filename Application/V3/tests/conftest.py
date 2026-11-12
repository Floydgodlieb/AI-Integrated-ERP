"""
Shared test setup.

Two kinds of tests:
  * offline tests  - no Odoo needed (safety rules, error cleaning)
  * Odoo tests     - need a running Odoo with the seed data (Setup/seed_odoo.py) and the ai_agent user.
                     They are SKIPPED automatically when Odoo is not reachable.

Login for the Odoo tests comes from, in this order:
  TEST_ODOO_URL / TEST_ODOO_DB / TEST_ODOO_USER / TEST_ODOO_PASS environment variables, or
  Application/V3/.env  (the same file the app uses).

NOTE: the Odoo tests create a few DRAFT quotations and invoices in that database.
Use a test database, or restore your backup afterwards, if that matters to you.
"""
import os
import socket
import sys
import tempfile
from pathlib import Path

import pytest
from dotenv import dotenv_values

V3_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(V3_DIR))                     # so "import backend..." works


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


_env_file = dotenv_values(V3_DIR / ".env")
ODOO = {
    "url": os.getenv("TEST_ODOO_URL") or _env_file.get("ODOO_URL") or "http://127.0.0.1:8069",
    "db": os.getenv("TEST_ODOO_DB") or _env_file.get("ODOO_DB") or "odoo",
    "user": os.getenv("TEST_ODOO_USER") or _env_file.get("ODOO_USER") or "ai_agent",
    "password": os.getenv("TEST_ODOO_PASS") or _env_file.get("ODOO_PASS") or "",
}

# Settings for the API tests. They must be set BEFORE backend.main / ollama are imported.
FAKE_OLLAMA_PORT = _free_port()
TEST_LOG_DIR = tempfile.mkdtemp(prefix="v3-tests-")
os.environ.update({
    "OLLAMA_HOST": f"http://127.0.0.1:{FAKE_OLLAMA_PORT}",
    "ODOO_URL": ODOO["url"], "ODOO_DB": ODOO["db"], "ODOO_USER": ODOO["user"], "ODOO_PASS": ODOO["password"],
    "AUDIT_LOG_PATH": os.path.join(TEST_LOG_DIR, "audit.jsonl"),
    "TEAMS_WEBHOOK_URL": "",
    "ODOO_ALLOW_AI_PRICES": "false",
})


def _odoo_reachable() -> bool:
    import xmlrpc.client
    try:
        return bool(xmlrpc.client.ServerProxy(f"{ODOO['url']}/xmlrpc/2/common").version())
    except Exception:
        return False


@pytest.fixture(scope="session")
def odoo_settings():
    if not ODOO["password"]:
        pytest.skip("No Odoo password: create Application/V3/.env or set TEST_ODOO_PASS")
    if not _odoo_reachable():
        pytest.skip(f"Odoo not reachable at {ODOO['url']}")
    return ODOO


@pytest.fixture()
def audit(tmp_path):
    from backend.audit import AuditLog
    return AuditLog(str(tmp_path / "audit.jsonl"))


@pytest.fixture()
def odoo(odoo_settings, audit):
    from backend.odoo_client import OdooClient
    return OdooClient(odoo_settings["url"], odoo_settings["db"], odoo_settings["user"],
                      odoo_settings["password"], timeout=15, audit=audit)


@pytest.fixture()
def offline_client(audit):
    from backend.odoo_client import OdooClient
    return OdooClient("http://127.0.0.1:9", "odoo", "nobody", "x", audit=audit, connect=False)
