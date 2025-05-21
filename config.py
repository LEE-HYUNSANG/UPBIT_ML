import json
import os


def load_config(path: str) -> dict:
    """Load JSON configuration from ``path``.``"""
    if not os.path.exists(path):
        return {}
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def save_config(data: dict, path: str) -> None:
    """Save ``data`` as JSON to ``path``."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
