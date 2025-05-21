from __future__ import annotations

import logging
from typing import Optional

from flask_socketio import SocketIO

from utils import send_telegram

logger = logging.getLogger(__name__)


_socketio: Optional[SocketIO] = None
_token: Optional[str] = None
_chat_id: Optional[str] = None


def init(socketio: Optional[SocketIO], token: Optional[str], chat_id: Optional[str]) -> None:
    global _socketio, _token, _chat_id
    _socketio = socketio
    _token = token
    _chat_id = chat_id


def notify(message: str) -> None:
    """Send message to browser via SocketIO and Telegram if enabled."""
    logger.debug("[NOTIFY] %s", message)
    if _socketio:
        _socketio.emit("notification", {"message": message})
    if _token and _chat_id:
        send_telegram(_token, _chat_id, message)


def notify_error(message: str, code: str) -> None:
    """Send error notification with code."""
    full = f"[{code}] {message}"
    logger.error(full)
    notify(full)
