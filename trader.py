"""Trading wrapper exposing Position and Trader classes."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import List

from bot.trader import UpbitTrader as BaseTrader


@dataclass
class Position:
    ticker: str
    amount: float
    buy_price: float
    strategy: str
    state: str = "open"
    entry_time: datetime | None = None
    exit_time: datetime | None = None

    def pnl(self, current_price: float) -> float:
        return (current_price - self.buy_price) / (self.buy_price + 1e-9) * 100


class Trader(BaseTrader):
    """High level trader maintaining open positions."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.positions: List[Position] = []
