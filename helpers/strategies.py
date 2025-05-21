"""Strategy signal helpers using formulas from JSON specifications."""

from __future__ import annotations

import ast
import logging
import re
from typing import Any, Dict

import pandas as pd

from helpers.utils.risk import load_risk_settings
from strategy_loader import load_strategies

logger = logging.getLogger(__name__)

# 전략 정의 로드
STRATEGY_SPECS = load_strategies()

# 레벨 문자열 -> 인덱스 매핑
LEVEL_INDEX = {
    "공격적": 0,
    "aggressive": 0,
    "중도적": 1,
    "moderate": 1,
    "보수적": 2,
    "conservative": 2,
}


def _sanitize(token: str) -> str:
    """Convert raw indicator token to a safe variable name."""
    return re.sub(r"[^a-zA-Z0-9_]", "", token).lower()


def _translate_formula(expr: str) -> str:
    """Replace indicator tokens with safe variable names."""

    pattern = r"[A-Za-z][A-Za-z0-9_%(),-]*"
    keywords = {"and", "or", "not", "True", "False"}

    def repl(match: re.Match[str]) -> str:
        token = match.group(0)
        if token in keywords:
            return token
        return _sanitize(token)

    return re.sub(pattern, repl, expr)


def safe_eval(expr: str, variables: Dict[str, Any]) -> Any:
    """Safely evaluate an expression with the given variables."""

    node = ast.parse(expr, mode="eval")
    for sub in ast.walk(node):
        if isinstance(sub, ast.Call):
            raise ValueError("function calls not allowed")
        if isinstance(sub, ast.Name) and sub.id not in variables:
            raise ValueError(f"unknown variable {sub.id}")
    compiled = compile(node, "<formula>", "eval")
    return eval(compiled, {"__builtins__": {}}, variables)


def df_to_market(df: pd.DataFrame, buy_price: float | None = None) -> Dict[str, float]:
    """Convert indicator DataFrame to a market data dictionary."""

    last = df.iloc[-1]
    prev1 = df.iloc[-2] if len(df) > 1 else last
    prev2 = df.iloc[-3] if len(df) > 2 else prev1

    data: Dict[str, float] = {}
    for col in df.columns:
        data[_sanitize(col)] = float(last[col])

    if "ema20" in df.columns:
        data["ema20_prev5"] = float(df["ema20"].iloc[-5])

    data.update(
        {
            "vol0": float(last.get("volume", 0)),
            "vol1": float(prev1.get("volume", 0)),
            "vol2": float(prev2.get("volume", 0)),
            "close1": float(prev1.get("close", 0)),
            "close2": float(prev2.get("close", 0)),
            "rsi1": float(prev1.get("rsi", 0)),
            "rsi2": float(prev2.get("rsi", 0)),
            "obv1": float(prev1.get("obv", 0)),
            "obv2": float(prev2.get("obv", 0)),
        }
    )

    if "volume" in df:
        data["ma_vol20"] = float(df["volume"].iloc[-20:].mean())
    if "high" in df:
        data["prevhigh20"] = float(df["high"].iloc[-21:-1].max())
        data["maxhigh20"] = float(df["high"].iloc[-20:].max())
        data["high80"] = float(df["high"].iloc[-80:].max())
    if "low" in df:
        data["minlow5"] = float(df["low"].iloc[-5:].min())
        data["minlow10"] = float(df["low"].iloc[-10:].min())
        data["minlow20"] = float(df["low"].iloc[-20:].min())
        data["low80"] = float(df["low"].iloc[-80:].min())
    if "atr" in df:
        data["atr10"] = float(df["atr"].iloc[-10:].mean())

    if buy_price is not None:
        data["entryprice"] = float(buy_price)

    return data


def _select_formula(spec, attr: str, level: str) -> str:
    """Return formula string for the given level."""

    formula = getattr(spec, attr, "")
    if formula:
        return formula
    levels = getattr(spec, f"{attr.split('_')[0]}_levels", [])
    idx = LEVEL_INDEX.get(level, 1)
    if levels and idx < len(levels):
        return " and ".join(levels[idx])
    return ""


def check_buy_signal(short_code: str, level: str, market: Dict[str, Any]) -> bool:
    """Evaluate buy formula and return True/False."""

    spec = STRATEGY_SPECS.get(short_code)
    if not spec:
        logger.warning("Unknown strategy %s", short_code)
        return False

    formula = _select_formula(spec, "buy_formula", level)
    if not formula:
        logger.warning("No buy formula for %s", short_code)
        return False

    try:
        expr = _translate_formula(formula)
        return bool(safe_eval(expr, market))
    except Exception as e:  # pragma: no cover - formula errors
        logger.warning("Buy formula error for %s: %s", short_code, e)
        return False


def check_sell_signal(
    short_code: str,
    level: str,
    market: Dict[str, Any],
    risk_conf: Dict[str, float] | None = None,
) -> bool:
    """Evaluate sell formula and return True/False."""

    spec = STRATEGY_SPECS.get(short_code)
    if not spec:
        logger.warning("Unknown strategy %s", short_code)
        return False

    formula = _select_formula(spec, "sell_formula", level)
    if not formula:
        logger.warning("No sell formula for %s", short_code)
        return False

    if risk_conf is None:
        risk_conf = load_risk_settings()

    entry = float(market.get("entryprice", 0))
    price = float(market.get("close", 0))
    max_dd = float(risk_conf.get("max_dd_per_coin", 0)) if risk_conf else 0
    if entry and max_dd and price <= entry * (1 - max_dd):
        return True

    try:
        expr = _translate_formula(formula)
        return bool(safe_eval(expr, market))
    except Exception as e:  # pragma: no cover - formula errors
        logger.warning("Sell formula error for %s: %s", short_code, e)
        return False


__all__ = [
    "check_buy_signal",
    "check_sell_signal",
    "df_to_market",
    "safe_eval",
]

