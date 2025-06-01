import json
import os

CONFIG_DIR = os.path.join(os.path.dirname(__file__), '01_alarm_control')
CONFIG_FILE = os.path.join(CONFIG_DIR, 'alarm_config.json')

DEFAULT_CONFIG = {
    "system_start_stop": True,
    "buy_monitoring": True,
    "order_execution": True,
    "system_alert": True,
    "ml_pipeline": True,
    "templates": {
        "buy": "[매수 체결] {symbol} @{price}",
        # {reason} will be replaced with '익절 매도' or '손절 매도'
        "sell": "[매도 체결] {symbol} | {reason} @{price}"
    }
}


def load_config(path: str = CONFIG_FILE) -> dict:
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return DEFAULT_CONFIG.copy()


def save_config(cfg: dict, path: str = CONFIG_FILE) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)


def is_enabled(category: str, path: str = CONFIG_FILE) -> bool:
    cfg = load_config(path)
    return bool(cfg.get(category, False))


def get_template(key: str, path: str = CONFIG_FILE) -> str:
    cfg = load_config(path)
    return cfg.get("templates", {}).get(key, DEFAULT_CONFIG["templates"].get(key, ""))
