"""Strategy specification loader."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List


@dataclass
class StrategySpec:
    """단일 전략 정의."""

    id: int
    name: str
    short_code: str
    buy_formula: str
    sell_formula: str
    buy_levels: List[List[str]]
    sell_levels: List[List[str]]
    params: dict


def load_strategies(path: str | Path = "config/strategies_master.json") -> Dict[str, StrategySpec]:
    """Return mapping of short_code to StrategySpec."""
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    result = {}
    for item in data:
        spec = StrategySpec(
            id=item.get("id"),
            name=item.get("name"),
            short_code=item.get("short_code"),
            buy_formula=item.get("buy_formula", ""),
            sell_formula=item.get("sell_formula", ""),
            buy_levels=item.get("buy_levels", []),
            sell_levels=item.get("sell_levels", []),
            params=item.get("params", {}),
        )
        result[spec.short_code] = spec
    return result


