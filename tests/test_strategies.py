import pandas as pd
from unittest.mock import patch

from helpers.strategies import check_buy_signal, check_sell_signal


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


def _patch_env(mock_ohlcv, mock_price, mock_ind, df):
    mock_ohlcv.return_value = df
    mock_price.return_value = float(df["close"].iloc[-1])
    mock_ind.side_effect = lambda d: d


@patch("helpers.strategies.calc_indicators")
@patch("helpers.strategies.pyupbit.get_current_price")
@patch("helpers.strategies.pyupbit.get_ohlcv")
@patch("helpers.strategies.calc_tis", return_value=100)
def test_buy_signals(_, mock_ohlcv, mock_price, mock_ind):
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
        _patch_env(mock_ohlcv, mock_price, mock_ind, df)
        assert check_buy_signal(strat, "KRW-TEST", "공격적"), strat


@patch("helpers.strategies.calc_indicators")
@patch("helpers.strategies.pyupbit.get_current_price")
@patch("helpers.strategies.pyupbit.get_ohlcv")
@patch("helpers.strategies.calc_tis", return_value=100)
def test_sell_signals(_, mock_ohlcv, mock_price, mock_ind):
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
        _patch_env(mock_ohlcv, mock_price, mock_ind, df)
        assert check_sell_signal(strat, "KRW-TEST", 1.0, "공격적"), strat
