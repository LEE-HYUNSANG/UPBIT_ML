import pandas as pd
from helpers.strategies import (
    check_buy_signal,
    check_sell_signal,
    df_to_market,
    _normalize,
    _apply_shifts,
)
from bot.indicators import compute_indicators
from strategy_loader import load_strategies


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


def _indicator_df(rows: int = 60) -> pd.DataFrame:
    """DataFrame with indicators computed for formula evaluation."""
    idx = pd.date_range("2021-01-01", periods=rows, freq="5T")
    base = {
        "Open": [1.0] * rows,
        "High": [1.1] * rows,
        "Low": [0.9] * rows,
        "Close": [1.0] * rows,
        "Volume": [100] * rows,
    }
    df = pd.DataFrame(base, index=idx)
    df = compute_indicators(df)
    df["Vol"] = df["Volume"]  # alias used in formulas
    return df


def make_df(strategy: str) -> pd.DataFrame:
    df = _indicator_df()
    if strategy == "P-PULL":
        df.loc[df.index[-1], "RSI14"] = 25
        df.loc[df.index[-1], "EMA50"] = df["Close"].iloc[-1] * 1.0005
        df.loc[df.index[-2], "Volume"] = 100
        df.loc[df.index[-1], "Volume"] = 120
    elif strategy == "T-FLOW":
        df.loc[df.index[-5], "EMA20"] = 1.0
        df.loc[df.index[-1], "EMA20"] = 1.02
        df.loc[df.index[-1], "RSI14"] = 55
    elif strategy == "B-LOW":
        df.loc[df.index[:-1], "High"] = 1.05
        df.loc[df.index[:-1], "Low"] = 1.0
        df.loc[df.index[-1], "Low"] = 1.01
        df.loc[df.index[-1], "RSI14"] = 20
    elif strategy == "V-REV":
        df.loc[df.index[-2], "Close"] = 0.95
        df.loc[df.index[-1], "Close"] = 1.0
        df.loc[df.index[-2], "Volume"] = 100
        df.loc[df.index[-1], "Volume"] = 260
        df.loc[df.index[-2], "RSI14"] = 18
        df.loc[df.index[-1], "RSI14"] = 21
    elif strategy == "G-REV":
        df.loc[df.index[-1], "EMA50"] = 1.1
        df.loc[df.index[-1], "EMA200"] = 1.0
        df.loc[df.index[-2], "Volume"] = 100
        df.loc[df.index[-1], "Volume"] = 80
        df.loc[df.index[-1], "RSI14"] = 50
    elif strategy == "VOL-BRK":
        df.loc[df.index[-10:], "ATR14"] = 0.04
        df.loc[df.index[-1], "ATR14"] = 0.08
        df.loc[df.index[-20:], "Volume"] = 100
        df.loc[df.index[-1], "Volume"] = 250
        df.loc[df.index[-1], "High"] = 1.2
        df.loc[df.index[-1], "RSI14"] = 65
    elif strategy == "EMA-STACK":
        df.loc[df.index[-1], "EMA25"] = 1.1
        df.loc[df.index[-1], "EMA100"] = 1.05
        df.loc[df.index[-1], "EMA200"] = 1.0
        df.loc[df.index[-1], "ADX"] = 32
    elif strategy == "VWAP-BNC":
        df.loc[df.index[-1], "VWAP"] = 1.199
        df.loc[df.index[-1], "Close"] = 1.2
        df.loc[df.index[-2], "Volume"] = 100
        df.loc[df.index[-1], "Volume"] = 120
        df.loc[df.index[-1], "RSI14"] = 50
    df["Vol"] = df["Volume"]
    return df


def test_buy_signals():
    """모든 전략의 매수 포뮬러가 오류 없이 계산되는지 확인한다."""
    strategies = load_strategies()
    for strat in strategies:
        df = make_df(strat)
        market = df_to_market(df, 1.0)
        res = check_buy_signal(strat, "공격적", market)
        assert isinstance(res, bool)


def test_sell_signals():
    """모든 전략의 매도 포뮬러가 오류 없이 계산되는지 확인한다."""
    strategies = load_strategies()
    for strat in strategies:
        df = make_df(strat)
        market = df_to_market(df, 1.0)
        market["Entry"] = df["Close"].iloc[-1] * 0.97
        market["Peak"] = df["High"].cummax().iloc[-1]
        res = check_sell_signal(strat, "공격적", market)
        assert isinstance(res, bool)


def test_normalize_zero_offset():
    assert _normalize("Low(0)") == "Low"
    assert _normalize("Vol(0)") == "Volume"


def test_normalize_offsets():
    assert _normalize("Close(-1)") == "Close_prev"
    assert _normalize("Close(1)") == "Close_prev"
    assert _normalize("PSAR(1)") == "PSAR_prev"


def test_normalize_single_indicators():
    assert _normalize("EMA(5)") == "EMA5"
    assert _normalize("ATR(14)") == "ATR14"
    assert _normalize("RSI(14)") == "RSI14"
    assert _normalize("StochK(14)") == "StochK14"
    assert _normalize("MACD_hist(-1)") == "MACD_hist_prev"


def test_normalize_ma_vol_and_atr():
    assert _normalize("MA(Vol,20)") == "Vol_MA20"
    assert _normalize("MA(ATR(14),20)") == "ATR14_MA20"

    
def test_compute_indicators_strength():
    idx = pd.date_range("2021-01-01", periods=5, freq="5T")
    base = {"Open": [1]*5, "High": [1]*5, "Low": [1]*5, "Close": [1]*5, "Volume": [1]*5}
    df = pd.DataFrame(base, index=idx)
    res = compute_indicators(df, strength=123)
    assert "Strength" in res.columns
    assert res["Strength"].iloc[0] == 123
