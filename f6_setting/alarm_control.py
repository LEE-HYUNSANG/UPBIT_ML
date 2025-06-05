"""Utility functions and defaults for Telegram alarm settings.

This module exposes helpers to load and save the alarm configuration that the
web UI consumes.  All Telegram message templates are centralized here so even
non‑developers can easily tweak notification text.  New templates can be added
by editing :data:`DEFAULT_CONFIG` or the JSON file saved by
:func:`save_config`.
"""

import json
import os

CONFIG_DIR = os.path.join(os.path.dirname(__file__), "01_alarm_control")
CONFIG_FILE = os.path.join(CONFIG_DIR, "alarm_config.json")

DEFAULT_CONFIG = {
    # Toggle each category to enable/disable specific notifications.
    "system_start_stop": True,
    "buy_monitoring": True,
    "order_execution": True,
    "system_alert": True,
    "ml_pipeline": True,
    # Message templates used throughout the project.  Placeholders wrapped in
    # curly braces will be replaced with runtime values.  Add new keys here and
    # call :func:`get_template` in your code to retrieve them.
    "templates": {
        # Sent when a buy signal is generated.
        "buy_signal": "[매수 시그널] {symbol} @{price}",
        # Sent after a successful market buy.
        "buy_success": "[매수 주문 성공] {symbol} 매수 금액: {amount:,}원 @{price}",
        # Sent when a sell is attempted.
        "sell_attempt": "[매도 시도] {symbol} @{price}",
        # Sent when a sell completes; {reason} will be '익절 매도' or '손절 매도'.
        # Final sell execution. Available fields: symbol, reason, amount, price,
        # profit.
        "sell_complete": (
            "[매도 완료] {symbol} | {reason} 매도 금액: {amount:,}원 @{price} "
            "이익:{profit}"
        ),
    }
}


def load_config(path: str = CONFIG_FILE) -> dict:
    """Return the alarm configuration from *path* or :data:`DEFAULT_CONFIG`."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return DEFAULT_CONFIG.copy()


def save_config(cfg: dict, path: str = CONFIG_FILE) -> None:
    """Write *cfg* to *path* creating the directory if necessary."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)


def is_enabled(category: str, path: str = CONFIG_FILE) -> bool:
    """Return ``True`` if *category* notifications are enabled."""
    cfg = load_config(path)
    return bool(cfg.get(category, False))


def get_template(key: str, path: str = CONFIG_FILE) -> str:
    """Return the template string for *key*.

    Parameters
    ----------
    key : str
        Template name, e.g. ``"buy_success"``.
    path : str, optional
        Alternate configuration file location.
    """
    cfg = load_config(path)
    return cfg.get("templates", {}).get(key, DEFAULT_CONFIG["templates"].get(key, ""))
