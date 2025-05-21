import json
import os


def load_risk_settings(path: str = "config/risk.json") -> dict:
    """리스크 관리 설정을 읽어 기본값을 제공한다."""
    if not os.path.exists(path):
        return {"max_dd_per_coin": 0.05}
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def save_risk_settings(data: dict, path: str = "config/risk.json") -> None:
    """리스크 관리 설정을 저장한다."""
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def load_manual_sells(path: str = "config/manual_sell.json") -> list[str]:
    """수동 매도 목록을 반환한다."""
    if not os.path.exists(path):
        return []
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):
            return [str(t) for t in data]
    except Exception:
        pass
    return []


def save_manual_sells(data: list[str], path: str = "config/manual_sell.json") -> None:
    """수동 매도 목록을 저장한다."""
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

