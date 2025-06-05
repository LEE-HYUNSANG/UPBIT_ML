"""Simple buy indicator based on RSI and EMA conditions."""

from __future__ import annotations

import pandas as pd


def add_basic_indicators(data: pd.DataFrame) -> pd.DataFrame:
    """Compute standard indicators used for entry decisions.

    Parameters
    ----------
    data : pandas.DataFrame
        OHLCV data containing at least a ``close`` column.

    Returns
    -------
    pandas.DataFrame
        New data frame with ``ema5``, ``ema20`` and ``rsi14`` columns added.
    """
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
    """Return a boolean mask for rows that meet the buy criteria.

    Parameters
    ----------
    data : pandas.DataFrame
        Data frame that must contain ``ema5``, ``ema20`` and ``rsi14``.

    Returns
    -------
    pandas.Series
        ``True`` for rows passing the RSI and trend checks.
    """
    required = {"ema5", "ema20", "rsi14"}
    if not required.issubset(data.columns):
        df = add_basic_indicators(data)
    else:
        df = data
    rsi_sel = (df["rsi14"] > 40) & (df["rsi14"] < 60)
    trend_sel = df["ema5"] > df["ema20"]
    return rsi_sel & trend_sel
