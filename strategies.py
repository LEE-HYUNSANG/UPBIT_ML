"""Strategy interface wrapping bot.strategy."""

from dataclasses import dataclass
from typing import Any

from bot.strategy import STRATS, select_strategy


@dataclass
class Strategy:
    name: str
    level: str = "중도적"

    def evaluate(self, df, tis: float, params: dict[str, Any]):
        ok, _ = select_strategy(self.name, df, tis, params)
        return ok

__all__ = ["Strategy", "STRATS", "select_strategy"]
