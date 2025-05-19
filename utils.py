import json
import logging
import os
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

    If the file is missing or malformed, or if required keys are
    missing/empty, an error is printed and logged and the process exits.
    When Telegram details are available via the file or environment
    variables the same message is sent there as well.
    """

    def alert(msg: str, secrets: dict | None = None) -> None:
        print(msg)
        logging.error(msg)
        token = os.getenv("TELEGRAM_TOKEN")
        chat = os.getenv("TELEGRAM_CHAT_ID")
        if secrets:
            token = secrets.get("TELEGRAM_TOKEN", token)
            chat = secrets.get("TELEGRAM_CHAT_ID", chat)
        if token and chat:
            send_telegram(token, chat, msg)

    try:
        with open(path, encoding="utf-8") as f:
            secrets = json.load(f)
    except FileNotFoundError:
        alert(f"[ERROR] Required file '{path}' not found.")
        sys.exit(1)
    except PermissionError:
        alert(f"[ERROR] No permission to read '{path}'.")
        sys.exit(1)
    except json.JSONDecodeError as e:
        alert(f"[ERROR] Failed to parse '{path}': {e}")
        sys.exit(1)

    missing = [key for key in required if not secrets.get(key)]
    if missing:
        alert(f"[ERROR] Missing required secrets: {', '.join(missing)}", secrets)
        sys.exit(1)

    return secrets
