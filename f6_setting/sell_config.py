import json
import os

DEFAULTS = {
    "TP_PCT": 1.5,
}


def load_sell_config(path: str = "config/f6_sell_settings.json") -> dict:
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


def save_sell_config(cfg: dict, path: str = "config/f6_sell_settings.json") -> None:
    data = load_sell_config(path)
    data.update({k: cfg[k] for k in cfg if k in DEFAULTS})
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
