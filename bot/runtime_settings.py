from dataclasses import dataclass, field
from datetime import datetime
import json

@dataclass
class RuntimeSettings:
    """앱 실행 중 변경되는 설정 값을 한곳에서 관리"""
    running: bool = False
    strategy: str = "M-BREAK"
    tp: float = 0.02
    sl: float = 0.01
    funds: int = 1_000_000
    max_amount: int = 500_000
    buy_amount: int = 100_000
    max_positions: int = 5
    slippage: float = 0.1
    balance_action: str = "alert"
    run_time: str = "09:00-22:00"
    rebalance: str = "1d"
    event_stop: str = ""
    backtest: str = "OFF"
    candle: str = "5m"
    fee: float = 0.05
    tune: str = ""
    ai_opt: str = "OFF"
    exchange: str = "UPBIT"
    tg_on: bool = True
    events: list[str] = field(default_factory=lambda: ["BUY", "SELL", "STOP"])
    notify_from: str = "08:00"
    notify_to: str = "22:00"
    updated: str = datetime.now().strftime("%Y-%m-%d")

    def update_timestamp(self) -> None:
        self.updated = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def to_dict(self) -> dict:
        """현재 설정을 dict 형태로 반환"""
        return self.__dict__.copy()

settings = RuntimeSettings()


def load_from_file(path: str = "config/config.json") -> None:
    """config.json 값을 읽어 settings 에 반영"""
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        return
    settings.strategy = data.get("strategy", settings.strategy)
    params = data.get("params", {})
    settings.tp = params.get("tp", settings.tp)
    settings.sl = params.get("sl", settings.sl)
    settings.funds = data.get("amount", settings.funds)
    settings.max_positions = data.get("max_positions", settings.max_positions)
    settings.max_amount = data.get("max_amount", settings.max_amount)
    settings.buy_amount = data.get("buy_amount", settings.buy_amount)
    settings.slippage = data.get("slippage", settings.slippage)
    settings.balance_action = data.get("balance_action", settings.balance_action)

