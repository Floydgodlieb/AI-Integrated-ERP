import os
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
import json
import logging

import anyio
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

from backend.odoo_client import OdooClient, OdooError
from backend.agent import ConversationAgent
from backend.audit import AuditLog

V3_DIR = Path(__file__).parent.parent
load_dotenv(V3_DIR / '.env')
logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
log = logging.getLogger("backend")


def _env_bool(name: str, default: bool = False) -> bool:
    return os.getenv(name, str(default)).strip().lower() in ("1", "true", "yes", "on")


ODOO_URL = os.getenv('ODOO_URL', 'http://127.0.0.1:8069')
ODOO_DB = os.getenv('ODOO_DB', 'odoo')
ODOO_USER = os.getenv('ODOO_USER', '')
ODOO_PASS = os.getenv('ODOO_PASS', '')
TEAMS_WEBHOOK_URL = os.getenv('TEAMS_WEBHOOK_URL', '')
ODOO_TIMEOUT = float(os.getenv('ODOO_TIMEOUT', '30'))
ODOO_READ_LIMIT = int(os.getenv('ODOO_READ_LIMIT', '50'))
ODOO_ALLOW_AI_PRICES = _env_bool('ODOO_ALLOW_AI_PRICES', False)
AUDIT_LOG_PATH = os.getenv('AUDIT_LOG_PATH', 'logs/audit.jsonl')
if not os.path.isabs(AUDIT_LOG_PATH):
    AUDIT_LOG_PATH = str(V3_DIR / AUDIT_LOG_PATH)
# Only the chat UI may call this API from a browser (was "*": any website).
CORS_ORIGINS = [o.strip() for o in os.getenv(
    'CORS_ORIGINS', 'http://localhost:5173,http://127.0.0.1:5173').split(',') if o.strip()]

audit = AuditLog(AUDIT_LOG_PATH)
agent: ConversationAgent | None = None


def ensure_agent():
    global agent
    if agent is not None:
        return agent
    if not ODOO_USER or not ODOO_PASS:
        log.error("Odoo credentials not configured (set ODOO_USER and ODOO_PASS in .env)")
        return None
    try:
        odoo = OdooClient(ODOO_URL, ODOO_DB, ODOO_USER, ODOO_PASS, TEAMS_WEBHOOK_URL,
                          timeout=ODOO_TIMEOUT, read_limit=ODOO_READ_LIMIT,
                          allow_ai_prices=ODOO_ALLOW_AI_PRICES, audit=audit)
        agent = ConversationAgent(odoo)
        log.info("Connected to Odoo %s as '%s' (database '%s')", ODOO_URL, ODOO_USER, ODOO_DB)
    except (OdooError, ConnectionError, OSError) as e:
        log.error("Odoo connection failed: %s", e)
    return agent


@asynccontextmanager
async def lifespan(app: FastAPI):
    ensure_agent()
    yield


app = FastAPI(title="Odoo AI Agent API", version="3.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=False,
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["Content-Type"],
)


class ChatRequest(BaseModel):
    message: str
    conversation_id: str | None = None


class ConfirmRequest(BaseModel):
    approved: bool


@app.get("/api/health")
async def health():
    a = ensure_agent()
    if a is None:
        return {"status": "error", "message": "Odoo not connected"}
    try:
        version = await anyio.to_thread.run_sync(a.odoo.version)
    except OdooError as e:
        return {"status": "error", "message": str(e)}
    return {"status": "ok", "odoo_version": version, "odoo_user": ODOO_USER}


def _sse(event: dict) -> dict:
    content = event["content"]
    return {"event": event["type"],
            "data": json.dumps(content) if isinstance(content, (dict, list)) else content}


@app.post("/api/chat")
async def chat(req: ChatRequest):
    if ensure_agent() is None:
        raise HTTPException(status_code=503, detail="Odoo not connected")

    conv_id = req.conversation_id or uuid.uuid4().hex[:12]

    async def event_generator():
        stream = agent.chat_stream(conv_id, req.message)
        try:
            while True:
                # Run each step of the (blocking) agent in a worker thread. abandon_on_cancel lets us
                # stop waiting when the browser disconnects, instead of keeping the thread busy forever.
                event = await anyio.to_thread.run_sync(next, stream, None, abandon_on_cancel=True)
                if event is None:
                    break
                yield _sse(event)
        except Exception as e:                      # e.g. Ollama not running: tell the user instead of a broken stream
            log.exception("chat failed")
            message = str(e) if isinstance(e, OdooError) else f"{type(e).__name__}: {str(e)[:200]}"
            yield {"event": "token", "data": f"Sorry, something went wrong in the backend ({message})."}
            yield {"event": "done", "data": ""}
        finally:
            # If the browser went away while an approval was waiting, release it (nothing is created).
            agent.cancel_pending(conv_id, reason="client_disconnected")
            try:
                stream.close()          # the agent was paused (not running): stop it for good ...
                agent.discard_pending(conv_id, reason="client_disconnected")   # ... and remove its approval
            except ValueError:
                pass                    # still running in its worker thread: it sees the cancel and cleans up itself

    return EventSourceResponse(event_generator())


@app.get("/api/conversation/{conv_id}")
async def get_conversation(conv_id: str):
    a = ensure_agent()
    if a is None:
        raise HTTPException(status_code=503, detail="Odoo not connected")
    history = a.get_history(conv_id)
    if history is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return {"messages": history}


@app.post("/api/confirm/{conv_id}")
async def confirm(conv_id: str, req: ConfirmRequest):
    if ensure_agent() is None:
        raise HTTPException(status_code=503, detail="Odoo not connected")
    if conv_id not in agent.pending_confirms:
        raise HTTPException(status_code=404, detail="No pending confirmation for this conversation (it may have expired)")
    audit.write("approval_answered", conv_id=conv_id, approved=req.approved)
    agent.set_confirmation(conv_id, req.approved)
    return {"status": "ok", "approved": req.approved}


@app.delete("/api/conversation/{conv_id}")
async def clear_conversation(conv_id: str):
    if agent is not None:
        agent.cancel_pending(conv_id, reason="conversation_cleared")
        agent.clear_history(conv_id)
        agent.pending_confirms.pop(conv_id, None)
        agent.pending_events.pop(conv_id, None)
    return {"status": "cleared"}
