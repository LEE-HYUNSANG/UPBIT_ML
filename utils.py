import json
import logging
import sys
from typing import Iterable
import requests


def send_telegram(token: str, chat_id: str, text: str) -> None:
    """Send a message via Telegram bot API."""
    try:
        requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            data={"chat_id": chat_id, "text": text},
            timeout=5,
        )
    except Exception as e:
        logging.error(f"Telegram send failed: {e}")


def load_secrets(
    path: str = "config/secrets.json",
    required: Iterable[str] = (
        "UPBIT_KEY",
        "UPBIT_SECRET",
        "TELEGRAM_TOKEN",
    ),
) -> dict:
    """Load secrets from ``path`` and ensure required fields exist.

    If the file is missing, unreadable or lacks required keys, the
    application prints an error, logs it and exits with status 1.
    A Telegram message is sent when token and chat id are available.
    """
    try:
        with open(path, encoding="utf-8") as f:
            secrets = json.load(f)
    except FileNotFoundError:
        msg = f"[ERROR] Required file '{path}' not found."
        print(msg)
        logging.error(msg)
        sys.exit(1)
    except PermissionError:
        msg = f"[ERROR] No permission to read '{path}'."
        print(msg)
        logging.error(msg)
        sys.exit(1)
    except json.JSONDecodeError as e:
        msg = f"[ERROR] Failed to parse '{path}': {e}"
        print(msg)
        logging.error(msg)
        sys.exit(1)

    missing = [key for key in required if not secrets.get(key)]
    if missing:
        msg = f"[ERROR] Missing required secrets: {', '.join(missing)}"
        print(msg)
        logging.error(msg)
        token = secrets.get("TELEGRAM_TOKEN")
        chat_id = secrets.get("TELEGRAM_CHAT_ID")
        if token and chat_id:
            send_telegram(token, chat_id, msg)
        sys.exit(1)

    return secrets
