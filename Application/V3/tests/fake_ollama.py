"""
A scripted stand-in for Ollama, used ONLY by the tests.

It speaks the same HTTP API as Ollama (POST /api/chat) but never runs a model:
the answer depends on a keyword in the last user message. That makes the tests
fast, repeatable, and runnable without a GPU. It also lets us reproduce mistakes
the real llama3.1 made (e.g. sending a list of fields as text).
"""
import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


def _script(messages, has_tools):
    last = messages[-1]
    if last["role"] == "tool":
        return {"text": "Here is the result."}
    text = last["content"].lower()
    if not has_tools:
        return {"text": "ok"}
    if "fields as text" in text:          # what the real llama3.1 sent on Floyd's PC
        return {"tool": ("odoo_search_read", {"model": "res.partner", "domain": "[]",
                                              "fields": "['name', 'email', 'phone']"})}
    if "customers" in text:
        return {"tool": ("odoo_search_read", {"model": "res.partner", "domain": [[]], "fields": ["name", "id"]})}
    if "system users" in text:
        return {"tool": ("odoo_search_read", {"model": "res.users", "domain": [], "fields": ["login"]})}
    if "order for pepsi" in text:
        return {"tool": ("odoo_create", {"model": "sale.order", "values": {
            "partner_id": "Pepsi", "product_id": "Chair", "product_uom_qty": 2}})}
    if "invoice for pepsi" in text:        # note: the AI invents a price of 10.00 (list price is 50.00)
        return {"tool": ("odoo_create", {"model": "account.move", "values": {
            "partner_id": "Pepsi", "move_type": "out_invoice",
            "invoice_line_ids": [[0, 0, {"product_id": "Chair", "quantity": 3, "price_unit": 10.0}]]}})}
    if "unknown customer" in text:
        return {"tool": ("odoo_create", {"model": "sale.order", "values": {
            "partner_id": "Nonexistent Corp XYZ", "product_id": "Chair", "product_uom_qty": 1}})}
    return {"text": "Hello! Which customer, product and quantity?"}


class _Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        out = _script(body["messages"], bool(body.get("tools")))
        base = {"model": body["model"], "created_at": "2026-01-01T00:00:00Z"}
        self.send_response(200)
        self.send_header("Content-Type", "application/x-ndjson")
        self.end_headers()
        if "tool" in out:
            name, args = out["tool"]
            message = {"role": "assistant", "content": "", "tool_calls": [{"function": {"name": name, "arguments": args}}]}
            self.wfile.write((json.dumps({**base, "message": message, "done": True}) + "\n").encode())
        elif body.get("stream", True):
            for word in out["text"].split(" "):
                self.wfile.write((json.dumps({**base, "message": {"role": "assistant", "content": word + " "},
                                              "done": False}) + "\n").encode())
            self.wfile.write((json.dumps({**base, "message": {"role": "assistant", "content": ""},
                                          "done": True}) + "\n").encode())
        else:
            self.wfile.write((json.dumps({**base, "message": {"role": "assistant", "content": out["text"]},
                                          "done": True}) + "\n").encode())


def start(port: int) -> ThreadingHTTPServer:
    server = ThreadingHTTPServer(("127.0.0.1", port), _Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server
