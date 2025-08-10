import logging
import os

import requests
from dotenv import load_dotenv

load_dotenv()


def call_yandex_gpt(question: str) -> str:
    folder_id = os.getenv("YANDEX_FOLDER_ID")
    yandex_authorization = os.getenv("YANDEX_AUTHORIZATION")

    logging.info(f"[YandexGPT] folder_id: {folder_id}")

    headers = {
        "Authorization": yandex_authorization,
        "Content-Type": "application/json"
    }

    url = "https://llm.api.cloud.yandex.net/foundationModels/v1/completion"

    payload = {
        "modelUri": f"gpt://{folder_id}/yandexgpt/latest",
        "completionOptions": {
            "stream": False,
            "temperature": 0.4,
            "maxTokens": 1000
        },
        "messages": [
            {"role": "system",
             "text": "You are a professional legal assistant. Answer briefly and clearly."},
            {"role": "user", "text": question}
        ]
    }

    try:
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()
        result = response.json()
        logging.info(f"[YandexGPT] result: {result}")
        return result['result']['alternatives'][0]['message']['text']
    except requests.exceptions.HTTPError as http_err:
        logging.error(f"❌ HTTP error from YandexGPT: {http_err} | Response: {response.text}")
        return "⚠️ Error when contacting YandexGPT (HTTP)"
    except Exception as e:
        logging.error(f"❌ Unknown error when contacting YandexGPT: {e}")
        return "⚠️ Error when contacting YandexGPT"
