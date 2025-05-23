import json
import os
import threading

POS_FILE = "config/active_positions.json"
_LOCK = threading.Lock()


def load_open_positions(path: str | None = None) -> dict:
    """활성 포지션 파일을 읽어 반환한다."""
    target = path or POS_FILE
    if not os.path.exists(target):
        return {}
    try:
        with open(target, encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            return data
    except Exception:
        pass
    return {}


def save_open_positions(data: dict, path: str | None = None) -> None:
    """현재 포지션 정보를 파일에 저장한다."""
    target = path or POS_FILE
    os.makedirs(os.path.dirname(target), exist_ok=True)
    with _LOCK:
        with open(target, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
