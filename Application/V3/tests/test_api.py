"""
End-to-end tests of the V3 API: browser -> API -> agent -> (scripted) AI -> Odoo.
The AI is the scripted stand-in from fake_ollama.py, so these test the backend, not llama3.1.
Skipped when Odoo is not running.
"""
import json
import threading
import time
from collections import Counter

import httpx
import pytest

import conftest
import fake_ollama


def _free_port():
    return conftest._free_port()


@pytest.fixture(scope="module")
def api(odoo_settings):
    import uvicorn
    from backend import main as backend_main

    ollama_server = fake_ollama.start(conftest.FAKE_OLLAMA_PORT)
    port = _free_port()
    server = uvicorn.Server(uvicorn.Config(backend_main.app, host="127.0.0.1", port=port, log_level="warning"))
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    for _ in range(100):
        if server.started:
            break
        time.sleep(0.1)
    yield f"http://127.0.0.1:{port}", backend_main
    server.should_exit = True
    thread.join(timeout=5)
    ollama_server.shutdown()


def chat(base, message, conv_id, approve=None, timeout=30):
    """Send a chat message; returns the list of (event, data) pairs. Answers an approval if asked."""
    events = []
    with httpx.stream("POST", f"{base}/api/chat", json={"message": message, "conversation_id": conv_id},
                      timeout=timeout) as response:
        buffer = ""
        for chunk in response.iter_text():
            buffer += chunk
            while "\r\n\r\n" in buffer:
                block, buffer = buffer.split("\r\n\r\n", 1)
                lines = block.split("\r\n")
                name = next((l[7:] for l in lines if l.startswith("event: ")), None)
                data = "\n".join(l[6:] for l in lines if l.startswith("data: "))
                events.append((name, data))
                if name == "confirmation_required" and approve is not None:
                    httpx.post(f"{base}/api/confirm/{conv_id}", json={"approved": approve})
    return events


def tool_result(events):
    return json.loads(next(d for e, d in events if e == "tool_call"))["result"]


def test_health_reports_odoo_version(api):
    base, _ = api
    body = httpx.get(f"{base}/api/health").json()
    assert body["status"] == "ok" and body["odoo_version"]


def test_read_customers(api):
    base, _ = api
    rows = tool_result(chat(base, "show all customers", "read-1"))
    assert any(r["name"] == "Pepsi" for r in rows)


def test_fields_sent_as_text_no_longer_break_the_read(api):
    base, _ = api
    rows = tool_result(chat(base, "show customers with fields as text", "read-2"))
    assert isinstance(rows, list) and "email" in rows[0]


def test_reading_system_users_is_refused(api):
    base, _ = api
    assert "not allowed" in tool_result(chat(base, "show system users", "read-3"))["error"]


def test_approved_invoice_is_draft_with_odoo_price(api):
    base, _ = api
    result = tool_result(chat(base, "create an invoice for pepsi", "create-1", approve=True))
    assert result["status"] == "success" and result["state"] == "draft"
    assert "Prices were taken from Odoo" in result["note"]


def test_declined_order_creates_nothing(api):
    base, _ = api
    assert tool_result(chat(base, "create an order for pepsi", "create-2", approve=False))["status"] == "cancelled"


def test_unknown_customer_is_rejected(api):
    base, _ = api
    assert "Could not find" in tool_result(chat(base, "order for unknown customer", "create-3"))["error"]


def test_twenty_parallel_chats(api):
    base, _ = api
    outcomes = []

    def one(i):
        try:
            rows = tool_result(chat(base, "show all customers", f"par-{i}"))
            outcomes.append("ok" if isinstance(rows, list) else "error")
        except Exception as e:
            outcomes.append(type(e).__name__)

    threads = [threading.Thread(target=one, args=(i,)) for i in range(20)]
    [t.start() for t in threads]
    [t.join() for t in threads]
    assert Counter(outcomes) == Counter({"ok": 20})


def test_abandoned_approvals_do_not_freeze_the_server(api):
    # Before: after 40 browsers closed during an approval, every new chat hung forever.
    base, backend_main = api
    for i in range(45):
        with httpx.stream("POST", f"{base}/api/chat", json={"message": "create an order for pepsi",
                                                            "conversation_id": f"gone-{i}"}, timeout=15) as r:
            for chunk in r.iter_text():
                if "confirmation_required" in chunk:
                    break                            # close the connection without answering
    time.sleep(1.5)
    started = time.time()
    events = chat(base, "hello", "after-abandon", timeout=10)
    assert ("done", "") in events and time.time() - started < 5
    assert not backend_main.agent.pending_confirms
    reasons = Counter(r.get("reason") for r in backend_main.audit.read_all() if r["event"] == "approval_expired")
    assert reasons["client_disconnected"] >= 45


def test_unanswered_approval_expires(api, monkeypatch):
    base, _ = api
    from backend import agent as agent_module
    monkeypatch.setattr(agent_module, "APPROVAL_TIMEOUT_SECONDS", 1)
    result = tool_result(chat(base, "create an order for pepsi", "slow-user"))   # never answers
    assert result["status"] == "expired"
    assert httpx.post(f"{base}/api/confirm/slow-user", json={"approved": True}).status_code == 404
