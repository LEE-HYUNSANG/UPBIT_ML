"""Simple buy indicator based on RSI and EMA conditions."""

from __future__ import annotations

import pandas as pd


def add_basic_indicators(data: pd.DataFrame) -> pd.DataFrame:
    """Return copy of ``data`` with EMA5/EMA20/RSI14 columns added."""
    df = data.copy()
    df["ema5"] = df["close"].ewm(span=5, adjust=False).mean()
    df["ema20"] = df["close"].ewm(span=20, adjust=False).mean()
    delta = df["close"].diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.rolling(window=14, min_periods=14).mean()
    avg_loss = loss.rolling(window=14, min_periods=14).mean()
    rs = avg_gain / avg_loss
    df["rsi14"] = 100 - (100 / (1 + rs))
    return df


def buy_selector(data: pd.DataFrame) -> pd.Series:
    """Boolean mask where RSI and uptrend conditions are satisfied."""
    required = {"ema5", "ema20", "rsi14"}
    if not required.issubset(data.columns):
        df = add_basic_indicators(data)
    else:
        df = data
    rsi_sel = (df["rsi14"] > 40) & (df["rsi14"] < 60)
    trend_sel = df["ema5"] > df["ema20"]
    return rsi_sel & trend_sel
