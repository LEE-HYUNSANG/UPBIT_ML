import re
from typing import Any, Dict
import pandas as pd
from bot.strategy import select_strategy

# Risk level mapping for convenience
RISK_LEVELS = {"공격적": 0, "중도적": 1, "보수적": 2, "aggressive": 0, "moderate": 1, "conservative": 2}


def _normalize(formula: str) -> str:
    """Convert indicator function calls to column-friendly names."""

    def _repl_multi(match: re.Match) -> str:
        name, period, offset = match.group(1), match.group(2), match.group(3)
        result = f"{name}{period}"
        if offset:
            off = abs(int(offset))
            if off:
                result += "_prev" + (str(off) if off > 1 else "")
        return result

    def _repl_bb(match: re.Match) -> str:
        name = match.group(1)
        offset = match.group(2)
        result = name
        if offset:
            off = abs(int(offset))
            if off:
                result += "_prev" + (str(off) if off > 1 else "")
        return result

    def _repl_offset(match: re.Match) -> str:
        col, off = match.group(1), int(match.group(2))
        result = col
        if off != 0:
            off = abs(off)
            result += "_prev" + (str(off) if off > 1 else "")
        return result

    # Replace MA(Vol,20) -> Vol_MA20
    formula = re.sub(r"MA\((\w+),\s*(\d+)\)", r"\1_MA\2", formula)

    # 1) Bollinger bands first
    formula = re.sub(r"(BB_(?:upper|lower))\(\d+,\s*\d+(?:,\s*(-?\d+))?\)", _repl_bb, formula)

    # 2) Multi-argument indicators like MFI(14,-1)
    formula = re.sub(r"([A-Za-z_]+)\((\d+),\s*(-?\d+)\)", _repl_multi, formula)

    # 3) Single-argument indicators
    formula = re.sub(r"([A-Za-z_]+)\(([1-9]\d*)\)", lambda m: f"{m.group(1)}{m.group(2)}", formula)

    # 4) Offsets such as Close(-1) or PSAR(1)
    formula = re.sub(r"(\b[A-Za-z_][A-Za-z0-9_]*)\((-?\d+)\)", _repl_offset, formula)

    # 5) Rename Vol column to Volume
    formula = re.sub(r"\bVol(?=\b|_)", "Volume", formula)

    return formula


def _apply_shifts(df: pd.DataFrame, formula: str) -> pd.DataFrame:
    """Create shifted columns referenced in the formula."""
    df = df.copy()
    for base, direction, num in re.findall(r"([A-Za-z_][A-Za-z0-9_]*)_(prev|next)(\d*)", formula):
        offset = int(num or 1)
        col_name = f"{base}_{direction}{offset if offset > 1 else ''}"
        if col_name in df.columns or base not in df.columns:
            continue
        if direction == "prev":
            df[col_name] = df[base].shift(offset)
        else:
            df[col_name] = df[base].shift(-offset)
    return df


def evaluate_buy_signals(df: pd.DataFrame, strategy: Dict[str, Any], risk_level: Any) -> pd.Series:
    level_idx = RISK_LEVELS.get(risk_level, risk_level)
    formula = strategy['buy_formula_levels'][level_idx]
    expr = formula.replace(' and ', ' & ').replace(' or ', ' | ')
    expr = _normalize(expr)
    df = _apply_shifts(df, expr)
    return df.eval(expr, engine='python').astype(bool)


def df_to_market(df: pd.DataFrame, tis: float) -> Dict[str, Any]:
    return {"df": df.copy(), "tis": tis}


def check_buy_signal(strategy_name: str, level: str, market: Dict[str, Any]) -> bool:
    ok, _ = select_strategy(strategy_name, market['df'], market.get('tis', 0), {})
    return ok


def check_sell_signal(strategy_name: str, level: str, market: Dict[str, Any]) -> bool:
    # Placeholder: always signal sell in tests
    return True
