import os
import json
import threading

# 파일 동시 접근 방지를 위한 락
_LOCK = threading.Lock()


def _validate(data: dict) -> None:
    """숫자 범위와 타입을 확인한다."""
    max_invest = float(data.get("max_invest_per_coin", 0))
    buy_amt = float(data.get("buy_amount", 0))
    max_trades = int(data.get("max_concurrent_trades", 1))
    slippage = float(data.get("slippage_tolerance", 0))
    if max_invest < 0 or max_invest > 1_000_000_000:
        raise ValueError("max_invest_per_coin out of range")
    if buy_amt < 0 or buy_amt > 1_000_000_000:
        raise ValueError("buy_amount out of range")
    if max_trades < 1 or max_trades > 100:
        raise ValueError("max_concurrent_trades out of range")
    if slippage < 0 or slippage > 1:
        raise ValueError("slippage_tolerance out of range")

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
    _validate(data)
    data["updated"] = __import__("datetime").datetime.now().isoformat(timespec="seconds")
    # 락을 이용해 동시 접근을 제어한다
    with _LOCK:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
