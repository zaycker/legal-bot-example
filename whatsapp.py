import os
import sqlite3

import requests
from dotenv import load_dotenv

load_dotenv()

OPERATOR_CHAT_ID = os.getenv("WHATSAPP_CHAT_ID")


def get_chat_id(session_id: str) -> str | None:
    return OPERATOR_CHAT_ID


def send_to_whatsapp_greenapi(session_id: str, user_question: str, force: bool = False) -> bool:
    idInstance = os.getenv("GREEN_ID_INSTANCE")
    apiTokenInstance = os.getenv("GREEN_API_TOKEN")

    chat_id = get_chat_id(session_id)
    if not chat_id:
        return False

    conn = sqlite3.connect("chat_history.db")
    c = conn.cursor()
    c.execute("SELECT sender, message FROM messages WHERE session_id = ?", (session_id,))
    history = c.fetchall()
    conn.close()

    text = f"📨 New request from user [{session_id}]:\n"
    for sender, msg in history[-10:]:
        prefix = "👤" if sender == "user" else "🤖" if sender == "bot" else "👨‍💼"
        text += f"{prefix}: {msg}\n"
    if force:
        text += f"\n❗ The user requests to contact the operator:\n{user_question}"
    else:
        text += f"\n❗ Question: {user_question}"

    url = f"https://api.green-api.com/waInstance{idInstance}/sendMessage/{apiTokenInstance}"
    payload = {
        "chatId": chat_id,
        "message": text[:4096]
    }

    try:
        response = requests.post(url, json=payload)
        return response.status_code == 200
    except Exception as e:
        return False
