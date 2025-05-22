import pandas as pd
from helpers.strategies import (
    check_buy_signal,
    check_sell_signal,
    df_to_market,
    _normalize,
)


def _base_df(rows=80):
    idx = pd.date_range("2020-01-01", periods=rows, freq="5T")
    data = {
        "open": [1.0] * rows,
        "high": [1.1] * (rows - 1) + [1.2],
        "low": [0.95] * rows,
        "close": [1.0] * (rows - 1) + [1.2],
        "volume": [100] * (rows - 1) + [200],
        "ema5": [1.05] * (rows - 1) + [1.1],
        "ema20": [1.04] * (rows - 1) + [1.08],
        "ema60": [1.03] * (rows - 1) + [1.06],
        "ema25": [1.05] * rows,
        "ema50": [1.05] * rows,
        "ema100": [1.04] * rows,
        "ema200": [1.03] * rows,
        "obv": list(range(rows)),
        "rsi": [50] * rows,
        "atr": [0.04] * rows,
        "adx": [40] * rows,
        "vwap": [1.2] * rows,
    }
    return pd.DataFrame(data, index=idx)


def make_df(strategy: str) -> pd.DataFrame:
    df = _base_df()
    if strategy == "P-PULL":
        df.loc[df.index[-1], "rsi"] = 25
        df.loc[df.index[-1], "ema50"] = df["close"].iloc[-1] * 1.0005
        df.loc[df.index[-2], "volume"] = 100
        df.loc[df.index[-1], "volume"] = 120
    elif strategy == "T-FLOW":
        df.loc[df.index[-5], "ema20"] = 1.0
        df.loc[df.index[-1], "ema20"] = 1.02
        df.loc[df.index[-1], "rsi"] = 55
    elif strategy == "B-LOW":
        df.loc[df.index[:-1], "high"] = 1.05
        df.loc[df.index[:-1], "low"] = 1.0
        df.loc[df.index[-1], "low"] = 1.01
        df.loc[df.index[-1], "rsi"] = 20
    elif strategy == "V-REV":
        df.loc[df.index[-2], "close"] = 0.95
        df.loc[df.index[-1], "close"] = 1.0
        df.loc[df.index[-2], "volume"] = 100
        df.loc[df.index[-1], "volume"] = 260
        df.loc[df.index[-2], "rsi"] = 18
        df.loc[df.index[-1], "rsi"] = 21
    elif strategy == "G-REV":
        df.loc[df.index[-1], "ema50"] = 1.1
        df.loc[df.index[-1], "ema200"] = 1.0
        df.loc[df.index[-2], "volume"] = 100
        df.loc[df.index[-1], "volume"] = 80
        df.loc[df.index[-1], "rsi"] = 50
    elif strategy == "VOL-BRK":
        df.loc[df.index[-10:], "atr"] = 0.04
        df.loc[df.index[-1], "atr"] = 0.08
        df.loc[df.index[-20:], "volume"] = 100
        df.loc[df.index[-1], "volume"] = 250
        df.loc[df.index[-1], "high"] = 1.2
        df.loc[df.index[-1], "rsi"] = 65
    elif strategy == "EMA-STACK":
        df.loc[df.index[-1], "ema25"] = 1.1
        df.loc[df.index[-1], "ema100"] = 1.05
        df.loc[df.index[-1], "ema200"] = 1.0
        df.loc[df.index[-1], "adx"] = 32
    elif strategy == "VWAP-BNC":
        df.loc[df.index[-1], "vwap"] = 1.199
        df.loc[df.index[-1], "close"] = 1.2
        df.loc[df.index[-2], "volume"] = 100
        df.loc[df.index[-1], "volume"] = 120
        df.loc[df.index[-1], "rsi"] = 50
    return df


def test_buy_signals():
    for strat in [
        "M-BREAK",
        "P-PULL",
        "T-FLOW",
        "B-LOW",
        "V-REV",
        "G-REV",
        "VOL-BRK",
        "EMA-STACK",
        "VWAP-BNC",
    ]:
        df = make_df(strat)
        market = df_to_market(df, 1.0)
        assert check_buy_signal(strat, "공격적", market)


def test_sell_signals():
    for strat in [
        "M-BREAK",
        "P-PULL",
        "T-FLOW",
        "B-LOW",
        "V-REV",
        "G-REV",
        "VOL-BRK",
        "EMA-STACK",
        "VWAP-BNC",
    ]:
        df = make_df(strat)
        market = df_to_market(df, 1.0)
        assert check_sell_signal(strat, "공격적", market)


def test_normalize_zero_offset():
    assert _normalize("Low(0)") == "Low"
    assert _normalize("Vol(0)") == "Vol"
