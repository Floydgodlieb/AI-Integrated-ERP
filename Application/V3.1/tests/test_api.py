"""
End-to-end tests of the V3.1 API: browser -> API -> agent -> (scripted) AI -> Odoo.
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


def test_ambiguous_customer_is_asked_not_guessed(api, monkeypatch):
    base, _ = api
    from backend import agent as agent_module
    monkeypatch.setattr(agent_module, "APPROVAL_TIMEOUT_SECONDS", 1)   # if it regresses: fail fast, not hang
    events = chat(base, "create an invoice for jansen", "ambiguous-1")
    assert "More than one customer matches 'Jansen'" in tool_result(events)["error"]
    assert not any(e == "confirmation_required" for e, _ in events)   # nothing to approve, nothing created


@pytest.mark.parametrize("answer,expected", [("2", "Jansen Bouw"), ("jansen & zonen", "Jansen & Zonen")])
def test_pick_from_the_list_without_retyping(api, monkeypatch, answer, expected):
    base, _ = api
    from backend import agent as agent_module
    monkeypatch.setattr(agent_module, "APPROVAL_TIMEOUT_SECONDS", 1)
    conv = f"pick-{answer}"
    question = tool_result(chat(base, "create an invoice for jansen", conv))["error"]
    assert "1. Jansen & Zonen" in question and "2. Jansen Bouw" in question
    events = chat(base, answer, conv, approve=False)      # the scripted AI can't read "2": the backend handles it
    card = json.loads(next(d for e, d in events if e == "confirmation_required"))
    assert card["values"]["_resolved_partner_id_name"] == expected
    assert tool_result(events)["status"] == "cancelled"


def test_other_reply_is_a_new_request(api):
    base, backend_main = api
    chat(base, "create an invoice for jansen", "pick-new")
    events = chat(base, "hello", "pick-new")
    assert not any(e == "confirmation_required" for e, _ in events)
    assert "pick-new" not in backend_main.agent.pending_choices


def test_card_shows_odoo_prices_and_duplicate_warning(api, monkeypatch):
    base, _ = api
    from backend import agent as agent_module
    monkeypatch.setattr(agent_module, "APPROVAL_TIMEOUT_SECONDS", 1)
    chat(base, "create an invoice for pepsi", "dup-1", approve=True)              # first draft: 3 Chair
    events = chat(base, "create an invoice for pepsi", "dup-2", approve=False)    # same again
    card = json.loads(next(d for e, d in events if e == "confirmation_required"))
    assert card["review"]["total_untaxed"] == 150.0                              # AI sent 10.00; Odoo says 50.00
    assert card["values"]["invoice_line_ids"][0][2]["_resolved_product_id_price"] == 50.0
    assert any("Possible duplicate" in w for w in card["review"]["warnings"])   # warns, doesn't block
    assert tool_result(events)["status"] == "cancelled"


@pytest.mark.parametrize("variant", ["text", "dict", "qty-text", "plural"])
def test_order_lines_in_the_shapes_small_models_send(api, monkeypatch, variant):
    # Floyd's real llama3.1 kept answering "Which product and quantity should I include?"
    base, _ = api
    from backend import agent as agent_module
    monkeypatch.setattr(agent_module, "APPROVAL_TIMEOUT_SECONDS", 1)
    events = chat(base, f"sell variant {variant}", f"shape-{variant}", approve=False)
    card = json.loads(next(d for e, d in events if e == "confirmation_required"))
    line = card["values"]["order_line"][0][2]
    assert (line["_resolved_product_id_name"], line["product_uom_qty"]) == ("Chair", 3)


def test_unknown_product_gets_an_ai_suggestion_the_user_confirms(api, monkeypatch):
    base, _ = api
    from backend import agent as agent_module
    monkeypatch.setattr(agent_module, "APPROVAL_TIMEOUT_SECONDS", 1)
    question = tool_result(chat(base, "sell product premium chair", "suggest-1"))["error"]
    assert "No product named 'premium chair'. Did you mean:\n1. Ergonomic Chair" in question   # not accepted silently
    card = json.loads(next(d for e, d in chat(base, "1", "suggest-1", approve=False) if e == "confirmation_required"))
    assert card["values"]["order_line"][0][2]["_resolved_product_id_name"] == "Ergonomic Chair"


def test_ai_suggestion_that_is_not_a_real_product_is_ignored(api):
    base, _ = api
    error = tool_result(chat(base, "sell product golden thing", "suggest-2"))["error"]
    assert error == "Could not find a product named 'golden thing'."


def test_odd_search_limit_is_clamped():
    from backend.agent import ConversationAgent
    agent = ConversationAgent(odoo_client=None)
    assert [agent._lookup_args({"what": "products", "limit": n})["limit"] for n in (0, 100, "7", None, "x")] == [10, 50, 7, 10, 10]


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
        started = time.time()
        received = ""
        with httpx.stream("POST", f"{base}/api/chat", json={"message": "create an order for pepsi",
                                                            "conversation_id": f"gone-{i}"}, timeout=15) as r:
            for chunk in r.iter_text():
                received += chunk                    # the word can arrive split over two pieces (seen on Windows)
                if "confirmation_required" in received:
                    break                            # close the connection without answering
                # The server's keep-alive pings stop httpx timing out, so check the time ourselves.
                assert time.time() - started < 20, (
                    f"request {i + 1} of 45 got no approval prompt within 20 s - the server is probably out of "
                    f"free workers (abandoned approvals not released). Received so far: {received[-200:]!r}")
        assert "confirmation_required" in received, f"request {i + 1}: stream ended without an approval prompt"
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
