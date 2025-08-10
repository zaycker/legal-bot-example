import datetime
import logging
import os
import re
import sqlite3

from dotenv import load_dotenv
from fastapi import FastAPI, Request, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from faq_handler import generate_answer
from whatsapp import send_to_whatsapp_greenapi
from yandex_gpt import call_yandex_gpt

os.environ["CHROMA_TELEMETRY_ENABLED"] = "false"

load_dotenv()

def init_db():
    conn = sqlite3.connect("chat_history.db")
    c = conn.cursor()
    c.execute('''
              CREATE TABLE IF NOT EXISTS messages
              (
                  id
                  INTEGER
                  PRIMARY
                  KEY
                  AUTOINCREMENT,
                  session_id
                  TEXT,
                  sender
                  TEXT,
                  message
                  TEXT,
                  timestamp
                  TEXT
              )
              ''')
    c.execute('''
              CREATE TABLE IF NOT EXISTS chat_sessions
              (
                  session_id
                  TEXT
                  PRIMARY
                  KEY,
                  chat_id
                  TEXT
              )
              ''')
    conn.commit()
    conn.close()


init_db()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()]
)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def restrict_static_access(request: Request, call_next):
    path = request.url.path
    if path.startswith("/widget/"):
        origin = request.headers.get("origin", "")
        referer = request.headers.get("referer", "")
    return await call_next(request)


class ChatRequest(BaseModel):
    session_id: str
    question: str
    switch_to_operator: bool = False


class ChatResponse(BaseModel):
    answer: str


@app.post("/api/init-session")
async def init_session(request: Request):
    data = await request.json()
    contract_id = data.get("contract_id")
    logging.info(f"⚙️ Received init-session for: {contract_id}")
    return {"status": "ok"}


@app.post("/api/chat", response_model=ChatResponse)
async def chat(req: ChatRequest, request: Request):
    session_id = request.query_params.get("contract_id") or req.session_id
    user_message = req.question.strip()
    logging.info(f"Request from {session_id}: {user_message}")

    save_message(session_id, "user", user_message)

    if req.switch_to_operator:
        sent = send_to_whatsapp_greenapi(session_id,
                                         user_message or "[User requested operator]",
                                         force=True)
        response = "Chat history sent to a specialist." if sent else "WhatsApp error"
        save_message(session_id, "bot", response)
        return ChatResponse(answer=response)

    local_answer = generate_answer(user_message)
    if "No similar answer found" not in local_answer:
        save_message(session_id, "bot", local_answer)
        return ChatResponse(answer=local_answer)

    bot_response = call_yandex_gpt(user_message)
    save_message(session_id, "bot", bot_response)
    return ChatResponse(answer=bot_response)


@app.get("/api/messages/{session_id}")
async def get_messages(session_id: str, request: Request, x_client_source: str = Header(None)):
    if not x_client_source or x_client_source.strip().lower() != "moblaw.ru":
        raise HTTPException(status_code=403, detail="Access denied")

    conn = sqlite3.connect("chat_history.db")
    c = conn.cursor()
    c.execute("SELECT sender, message, timestamp FROM messages WHERE session_id = ? ORDER BY id ASC", (session_id,))
    messages = [{"sender": row[0], "message": row[1], "timestamp": row[2]} for row in c.fetchall()]
    conn.close()
    return {"messages": messages}


@app.post("/api/whatsapp-webhook")
async def whatsapp_webhook(request: Request):
    try:
        data = await request.json()
    except Exception as e:
        logging.error("❌ JSON error: %s", e)
        return {"status": "invalid json"}

    event_type = data.get("typeWebhook")
    if event_type not in ["incomingMessageReceived", "outgoingMessageReceived"]:
        return {"status": "skipped"}

    text_message = data.get("messageData", {}).get("textMessageData", {}).get("textMessage")
    chat_id = data.get("senderData", {}).get("chatId")
    expected_chat_id = os.getenv("WHATSAPP_CHAT_ID")

    if chat_id != expected_chat_id or not text_message:
        return {"status": "ignored"}

    match = re.match(r"\[?(\w+)\]?:?\s*(.*)", text_message)
    if match:
        session_id, operator_message = match.groups()
        save_message(session_id, "operator", operator_message)
    else:
        save_message("unknown", "operator", text_message)

    return {"status": "received"}


def save_message(session_id: str, sender: str, message: str):
    conn = sqlite3.connect("chat_history.db")
    c = conn.cursor()
    c.execute("INSERT INTO messages (session_id, sender, message, timestamp) VALUES (?, ?, ?, ?)",
              (session_id, sender, message, datetime.datetime.now().isoformat()))
    conn.commit()
    conn.close()


app.mount("/", StaticFiles(directory="static", html=True), name="static")
