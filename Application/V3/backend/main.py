import os
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
import json

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

from backend.odoo_client import OdooClient
from backend.agent import ConversationAgent

load_dotenv(Path(__file__).parent.parent / '.env')

ODOO_URL = os.getenv('ODOO_URL', 'http://localhost:8069')
ODOO_DB = os.getenv('ODOO_DB', 'odoo')
ODOO_USER = os.getenv('ODOO_USER', '')
ODOO_PASS = os.getenv('ODOO_PASS', '')
TEAMS_WEBHOOK_URL = os.getenv('TEAMS_WEBHOOK_URL', '')

agent: ConversationAgent | None = None


def ensure_agent():
    global agent
    if agent is not None:
        return agent
    if not ODOO_USER or not ODOO_PASS:
        print("Odoo credentials not configured (set ODOO_USER and ODOO_PASS in .env)")
        return None
    try:
        odoo = OdooClient(ODOO_URL, ODOO_DB, ODOO_USER, ODOO_PASS, TEAMS_WEBHOOK_URL)
        agent = ConversationAgent(odoo)
    except ConnectionError as e:
        print(f"Odoo connection failed: {e}")
    return agent


@asynccontextmanager
async def lifespan(app: FastAPI):
    ensure_agent()
    yield


app = FastAPI(title="Odoo AI Agent API", version="3.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    message: str
    conversation_id: str | None = None


class ConfirmRequest(BaseModel):
    approved: bool


@app.get("/api/health")
async def health():
    if agent is None:
        return {"status": "error", "message": "Odoo not connected"}
    return {"status": "ok"}


@app.post("/api/chat")
async def chat(req: ChatRequest):
    if ensure_agent() is None:
        raise HTTPException(status_code=503, detail="Odoo not connected")

    conv_id = req.conversation_id or uuid.uuid4().hex[:12]

    def event_generator():
        for event in agent.chat_stream(conv_id, req.message):
            yield {
                "event": event["type"],
                "data": json.dumps(event["content"]) if isinstance(event["content"], (dict, list)) else event["content"]
            }

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
        raise HTTPException(status_code=404, detail="No pending confirmation for this conversation")
    agent.set_confirmation(conv_id, req.approved)
    return {"status": "ok", "approved": req.approved}


@app.delete("/api/conversation/{conv_id}")
async def clear_conversation(conv_id: str):
    if agent is not None:
        agent.clear_history(conv_id)
        agent.pending_confirms.pop(conv_id, None)
        agent.pending_events.pop(conv_id, None)
    return {"status": "cleared"}
