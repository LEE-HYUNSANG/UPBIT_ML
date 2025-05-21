from __future__ import annotations

import logging
from typing import Optional

from flask_socketio import SocketIO

from utils import send_telegram, send_email

logger = logging.getLogger(__name__)


_socketio: Optional[SocketIO] = None
_token: Optional[str] = None
_chat_id: Optional[str] = None
_email: dict | None = None


def init(
    socketio: Optional[SocketIO],
    token: Optional[str],
    chat_id: Optional[str],
    email: dict | None = None,
) -> None:
    global _socketio, _token, _chat_id, _email
    _socketio = socketio
    _token = token
    _chat_id = chat_id
    _email = None
    if email and all(email.get(k) for k in ["host", "port", "user", "password", "to"]):
        _email = email
    elif email:
        logger.warning("Incomplete email configuration; email notifications disabled")


def notify(message: str) -> None:
    """Send message via SocketIO, Telegram and email (if configured)."""
    logger.debug("[NOTIFY] %s", message)
    if _socketio:
        _socketio.emit("notification", {"message": message})
    if _token and _chat_id:
        send_telegram(_token, _chat_id, message)
    if _email:
        send_email(
            _email["host"],
            int(_email["port"]),
            _email["user"],
            _email["password"],
            _email["to"],
            "Notification",
            message,
        )


def notify_error(message: str, code: str) -> None:
    """Send error notification with code."""
    full = f"[{code}] {message}"
    logger.error(full)
    notify(full)
