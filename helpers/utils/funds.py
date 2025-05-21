import os
import json

def load_fund_settings(path: str = "config/funds.json") -> dict:
    """자금 설정 파일을 읽어 반환한다."""
    if not os.path.exists(path):
        return {
            "max_invest_per_coin": 500000,
            "buy_amount": 100000,
            "max_concurrent_trades": 5,
            "slippage_tolerance": 0.001,
            "balance_exhausted_action": "알림",
            "updated": None,
        }
    with open(path, encoding="utf-8") as f:
        return json.load(f)

def save_fund_settings(data: dict, path: str = "config/funds.json") -> None:
    """자금 설정을 저장하고 업데이트 시각을 기록한다."""
    data["updated"] = __import__("datetime").datetime.now().isoformat(timespec="seconds")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
