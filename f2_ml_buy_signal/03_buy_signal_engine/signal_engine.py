import logging
import os
import re
from logging.handlers import RotatingFileHandler
from typing import Optional
from common_utils import ensure_utf8_stdout, setup_logging

import pandas as pd

from importlib import import_module

check_buy_signal_df = import_module("f2_ml_buy_signal.02_ml_buy_signal").check_buy_signal_df

os.makedirs("logs", exist_ok=True)
ensure_utf8_stdout()
setup_logging("F2", [os.path.join("logs", "F2_signal_engine.log")])


def reload_strategy_settings() -> None:
    """Placeholder for backward compatibility."""
    return None


def f2_signal(
    df_1m: pd.DataFrame,
    df_5m: pd.DataFrame,
    symbol: str = "",
    trades: Optional[pd.DataFrame] = None,
    calc_buy: bool = True,
    calc_sell: bool = True,
    strategy_codes: Optional[list[str]] = None,
) -> dict:
    """Return buy signal using lightweight ML model."""
    df_1m = df_1m.sort_values("timestamp").reset_index(drop=True)
    logging.info("Checking %s (calc_buy=%s, calc_sell=%s)", symbol, calc_buy, calc_sell)
    buy_signal = check_buy_signal_df(df_1m) if calc_buy else False
    result = {
        "symbol": symbol,
        "buy_signal": bool(buy_signal),
        "sell_signal": False,
        "buy_triggers": [],
        "sell_triggers": [],
    }
    logging.info("[%s] result: %s", symbol, result)
    return result


def eval_formula(
    formula: str,
    data_row: pd.Series,
    symbol: str = "",
    strat_code: str = "",
    data_df: Optional[pd.DataFrame] = None,
    entry: Optional[float] = None,
    peak: Optional[float] = None,
) -> bool:
    """Evaluate old strategy formulas for compatibility."""
    expr = formula
    expr = expr.replace("MA(Vol,20)", "Vol_MA20")
    expr = expr.replace("MA(ATR(14),20)", "ATR_14_MA20")

    base_fields = {
        "Close": "close",
        "Open": "open",
        "High": "high",
        "Low": "low",
        "Vol": "volume",
    }
    for fld, col in base_fields.items():
        pattern = rf"{fld}\((-?[0-9]+)\)"

        def _repl(m):
            off = int(m.group(1))
            if off == 0:
                val = data_row.get(col, 0)
            elif data_df is not None:
                idx = data_row.name + off
                if 0 <= idx < len(data_df):
                    val = data_df.iloc[idx].get(col, 0)
                else:
                    val = 0
            else:
                val = 0
            return str(float(val))

        expr = re.sub(pattern, _repl, expr)

    replacements = {
        "Close": data_row["close"],
        "Open": data_row["open"],
        "High": data_row["high"],
        "Low": data_row["low"],
        "Vol": data_row["volume"],
    }
    if "Entry" in formula or "EntryPrice" in formula:
        replacements["EntryPrice"] = replacements["Entry"] = entry if entry is not None else 0
    if "Peak" in formula:
        replacements["Peak"] = peak if peak is not None else 0

    ind_patterns = [
        "EMA",
        "RSI",
        "ATR",
        "MFI",
        "ADX",
        "MACD_line",
        "MACD_signal",
        "MACD_hist",
        "StochK",
        "StochD",
        "BB_upper",
        "BB_lower",
        "BB_mid",
        "BandWidth20",
        "BandWidth20_min20",
        "Vol_MA20",
        "ATR_14_MA20",
        "BuyQty_5m",
        "SellQty_5m",
        "VWAP",
        "Strength",
        "Tenkan",
        "Kijun",
        "SpanA",
        "SpanB",
        "Chikou",
        "DI_plus",
        "DI_minus",
        "PSAR",
        "MaxHigh5",
        "MaxHigh20",
        "MaxHigh60",
        "MaxHigh120",
        "MinLow5",
        "MinLow20",
        "MinLow60",
        "MinLow120",
    ]
    for key in ind_patterns:
        if key in expr:
            if key + "(" in expr:
                pattern = rf"{key}\(([^()]*)\)"
                matches = list(re.finditer(pattern, expr))
                for m in matches:
                    params = [p.strip() for p in m.group(1).split(',')]
                    period_val = params[0] if params else ""
                    offset_val = 0
                    if len(params) >= 2 and re.fullmatch(r"-?\d+", params[1]):
                        offset_val = int(params[1])
                    if key in ["EMA", "RSI", "ATR", "MFI", "ADX"]:
                        col_name = f"{key}_{period_val}"
                    elif key.startswith("Stoch"):
                        col_name = f"{key}_{period_val}"
                    elif key.startswith("BB_") or key.startswith("BandWidth") or key.startswith("Vol_MA"):
                        col_name = key
                    else:
                        col_name = key
                    if offset_val == 0:
                        value = data_row.get(col_name, None)
                    elif data_df is not None:
                        idx = data_row.name + offset_val
                        if 0 <= idx < len(data_df):
                            value = data_df.iloc[idx].get(col_name, None)
                        else:
                            value = None
                    else:
                        value = None
                    replacement_val = "0" if value is None or pd.isna(value) else f"{float(value)}"
                    expr = re.sub(re.escape(m.group(0)), replacement_val, expr)
            if key in data_row:
                if key == "SellQty_5m":
                    val = data_row[key]
                    val = 0 if pd.isna(val) else float(val)
                    replacement_val = f"({val} if {val} != 0 else 1e-8)"
                else:
                    replacement_val = "0" if pd.isna(data_row[key]) else f"{float(data_row[key])}"
                expr = re.sub(rf"\b{re.escape(key)}\b", replacement_val, expr)

    for name, val in replacements.items():
        expr = expr.replace(name, str(float(val)) if hasattr(val, "__float__") else str(val))
    expr = expr.replace("×", "*").replace("≤", "<=").replace("≥", ">=")
    try:
        result = eval(expr)
        if isinstance(result, (int, float)):
            result = bool(result)
        return bool(result)
    except Exception:
        return False
