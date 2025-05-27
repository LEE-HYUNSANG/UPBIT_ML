"""Utility functions to load and compile strategy formulas."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Callable, Dict
import ast

import pandas as pd

BASE_DIR = Path(__file__).resolve().parent
STRATEGY_JSON = BASE_DIR.parent / "strategies_master_pruned.json"


def _shift(col: str, shift_val: str | None) -> str:
    """Append a pandas shift operation if shift_val is provided."""
    if not shift_val or int(shift_val) == 0:
        return col
    return f"{col}.shift({abs(int(shift_val))})"


def _convert(formula: str) -> str:
    """Convert a textual formula to a pandas-friendly expression."""
    expr = formula

    patterns = [
        (r"EMA\((\d+)(?:,\s*(-?\d+))?\)", lambda m: _shift(f"df['ema_{m.group(1)}']", m.group(2))),
        (r"ATR\((\d+)(?:,\s*(-?\d+))?\)", lambda m: _shift(f"df['atr_{m.group(1)}']", m.group(2))),
        (r"RSI\((\d+)(?:,\s*(-?\d+))?\)", lambda m: _shift(f"df['rsi_{m.group(1)}']", m.group(2))),
        (r"MFI\((\d+)(?:,\s*(-?\d+))?\)", lambda m: _shift(f"df['mfi_{m.group(1)}']", m.group(2))),
        (r"MA\(Vol,(\d+)\)", lambda m: f"df['ma_vol_{m.group(1)}']"),
        (r"Vol\((\d+)\)", lambda m: f"df['vol_{m.group(1)}']"),
        (r"BB_lower\((\d+),(\d+)(?:,\s*(-?\d+))?\)",
         lambda m: _shift(f"df['bb_lower_{m.group(1)}_{m.group(2)}']", m.group(3))),
        (r"BB_upper\((\d+),(\d+)(?:,\s*(-?\d+))?\)",
         lambda m: _shift(f"df['bb_upper_{m.group(1)}_{m.group(2)}']", m.group(3))),
        (r"BB_mid\((\d+),(\d+)(?:,\s*(-?\d+))?\)",
         lambda m: _shift(f"df['bb_mid_{m.group(1)}_{m.group(2)}']", m.group(3))),
        (r"StochK\((\d+)(?:,\s*(-?\d+))?\)",
         lambda m: _shift(f"df['stoch_k_{m.group(1)}']", m.group(2))),
        (r"StochD\((\d+)(?:,\s*(-?\d+))?\)",
         lambda m: _shift(f"df['stoch_d_{m.group(1)}']", m.group(2))),
        (r"PSAR\((\d+)\)", lambda m: _shift("df['psar']", m.group(1))),
        (r"Tenkan\((\d+)(?:,\s*(-?\d+))?\)",
         lambda m: _shift(f"df['tenkan_{m.group(1)}']", m.group(2))),
        (r"Kijun\((\d+)(?:,\s*(-?\d+))?\)",
         lambda m: _shift(f"df['kijun_{m.group(1)}']", m.group(2))),
        (r"SpanA\(([-]?\d+)\)", lambda m: _shift("df['span_a']", m.group(1))),
        (r"SpanB\(([-]?\d+)\)", lambda m: _shift("df['span_b']", m.group(1))),
        (r"Close\(([-]?\d+)\)", lambda m: _shift("df['close']", m.group(1))),
        (r"Open\(([-]?\d+)\)", lambda m: _shift("df['open']", m.group(1))),
        (r"High\(([-]?\d+)\)", lambda m: _shift("df['high']", m.group(1))),
        (r"Low\(([-]?\d+)\)", lambda m: _shift("df['low']", m.group(1))),
    ]

    for pat, repl in patterns:
        expr = re.sub(pat, lambda m, r=repl: r(m), expr)

    # simple column names
    simple_map = {
        "Close": "df['close']",
        "Open": "df['open']",
        "High": "df['high']",
        "Low": "df['low']",
        "Strength": "df['strength']",
        "VWAP": "df['vwap']",
        "MaxSpan": "df['maxspan']",
        "BuyQty_5m": "df['buy_qty_5m']",
        "SellQty_5m": "df['sell_qty_5m']",
        "EntryPrice": "_get_col(df, 'entry_price', df['close'])",
        "Entry": "_get_col(df, 'entry_price', df['close'])",
        "Peak": "_get_col(df, 'peak', df['close'].cummax())",
    }
    for key, val in simple_map.items():
        expr = re.sub(rf"\b{key}\b", val, expr)

    expr = re.sub(r"MaxHigh(\d+)", lambda m: f"df['max_high_{m.group(1)}']", expr)
    expr = re.sub(r"MinLow(\d+)", lambda m: f"df['min_low_{m.group(1)}']", expr)

    return expr


def compile_formula(formula: str) -> Callable[[pd.DataFrame], pd.Series]:
    """Return a callable that evaluates the given formula against a DataFrame."""
    expr = _convert(formula)

    tree = ast.parse(expr, mode="eval")

    class BoolTransformer(ast.NodeTransformer):
        def visit_BoolOp(self, node: ast.BoolOp) -> ast.AST:
            self.generic_visit(node)
            op = ast.BitAnd() if isinstance(node.op, ast.And) else ast.BitOr()
            result = node.values[0]
            for val in node.values[1:]:
                result = ast.BinOp(left=result, op=op.__class__(), right=val)
            return result

    tree = BoolTransformer().visit(tree)
    ast.fix_missing_locations(tree)
    code = compile(tree, "<formula>", "eval")

    def _fn(df: pd.DataFrame) -> pd.Series:
        return eval(code)

    return _fn


def load_strategies(path: Path = STRATEGY_JSON) -> Dict[str, Dict[str, Callable[[pd.DataFrame], pd.Series]]]:
    """Load strategies from JSON and compile formulas."""
    data = json.loads(path.read_text())
    out: Dict[str, Dict[str, Callable[[pd.DataFrame], pd.Series]]] = {}
    for strat in data:
        short = strat["short_code"]
        out[short] = {
            "buy": compile_formula(strat["buy_formula"]),
            "sell": compile_formula(strat["sell_formula"]),
        }
    return out

