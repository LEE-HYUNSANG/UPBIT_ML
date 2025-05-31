import json
import os

DEFAULTS = {
    "ENTRY_SIZE_INITIAL": 10000,
    "MAX_SYMBOLS": 10,
    "MAX_RETRY": 3,
    "SLIP_MAX": 0.15,
    "ORDER_FAIL_RETRY": 3,
}


def load_buy_config(path: str = "config/f6_buy_settings.json") -> dict:
    data = DEFAULTS.copy()
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                file_data = json.load(f)
                if isinstance(file_data, dict):
                    data.update(file_data)
        except Exception:
            pass
    return data


def save_buy_config(cfg: dict, path: str = "config/f6_buy_settings.json") -> None:
    data = load_buy_config(path)
    data.update({k: cfg[k] for k in cfg if k in DEFAULTS})
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
