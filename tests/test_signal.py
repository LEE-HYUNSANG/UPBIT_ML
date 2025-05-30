import importlib
import logging
import pytest

try:
    import pandas as pd
    import numpy as np
except Exception:
    pandas_available = False
else:
    pandas_available = True

if pandas_available:
    from importlib import import_module
    _mod = import_module("f2_ml_buy_signal.03_buy_signal_engine.signal_engine")
    eval_formula = _mod.eval_formula
    f2_signal = _mod.f2_signal

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [F2] [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()],
)

@pytest.mark.skipif(not pandas_available, reason="pandas not available")
def test_eval_formula_basic():
    row = pd.Series({
        "close": 10,
        "open": 9,
        "high": 11,
        "low": 9,
        "volume": 100,
        "EMA_5": 9.5,
        "EMA_20": 9.0,
        "Vol_MA20": 100,
    })
    result = eval_formula("Close > EMA(5) and Vol(0) >= MA(Vol,20)", row)
    logging.info(f"[TEST] FORMULA | result={result}")
    assert result

@pytest.mark.skipif(not pandas_available, reason="pandas not available")
def test_f2_signal_output_structure():
    df = pd.DataFrame({
        "timestamp": pd.date_range('2020-01-01', periods=30, freq='T'),
        "open": np.linspace(1,30,30),
        "high": np.linspace(1.1,30.1,30),
        "low": np.linspace(0.9,29.9,30),
        "close": np.linspace(1,30,30),
        "volume": np.full(30,100)
    })
    result = f2_signal(df, df, symbol="TEST")
    logging.info(
        f"[TEST] TEST | Buy={result['buy_signal']} | Sell={result['sell_signal']}"
    )
    assert {"symbol", "buy_signal", "sell_signal", "buy_triggers", "sell_triggers"} <= result.keys()

@pytest.mark.skipif(not pandas_available, reason="pandas not available")
def test_f2_signal_buy_trigger():
    df = pd.DataFrame({
        "timestamp": pd.date_range("2021-01-01", periods=30, freq="T"),
        "open": np.linspace(1,30,30),
        "high": np.linspace(1.1,30.1,30),
        "low": np.linspace(0.9,29.9,30),
        "close": np.linspace(1,30,30),
        "volume": np.full(30,100)
    })
    result = f2_signal(df, df, symbol="TBUY")
    logging.info(
        f"[F2_TEST] BUY | Buy={result['buy_signal']} | Sell={result['sell_signal']}"
    )
    assert "buy_signal" in result


@pytest.mark.skipif(not pandas_available, reason="pandas not available")
def test_f2_signal_disable_all():
    df = pd.DataFrame({
        "timestamp": pd.date_range("2021-01-01", periods=30, freq="T"),
        "open": np.linspace(1, 30, 30),
        "high": np.linspace(1.1, 30.1, 30),
        "low": np.linspace(0.9, 29.9, 30),
        "close": np.linspace(1, 30, 30),
        "volume": np.full(30, 100),
    })
    result = f2_signal(df, df, symbol="NONE", calc_buy=False, calc_sell=False)
    assert not result["buy_signal"] and not result["sell_signal"]


@pytest.mark.skipif(not pandas_available, reason="pandas not available")
def test_eval_formula_numeric_comparison():
    row = pd.Series({"close": 10, "EMA_5": 9})
    res = eval_formula("Close > EMA(5)", row)
    logging.info(f"[F2_TEST] FORMULA_COMPARE | result={res}")
    assert res


@pytest.mark.skipif(not pandas_available, reason="pandas not available")
def test_eval_formula_single_param():
    row = pd.Series({"close": 1, "EMA_5": 10})
    assert not eval_formula("Close > EMA(5)", row)


@pytest.mark.skipif(not pandas_available, reason="pandas not available")
def test_eval_formula_with_offset():
    df = pd.DataFrame({"close": [1, 2, 3], "open": [1, 1, 1]})
    row = df.iloc[2]
    res = eval_formula("Close > Close(-1)", row, data_df=df)
    assert res


@pytest.mark.skipif(not pandas_available, reason="pandas not available")
def test_eval_formula_hyun_zero_division():
    hyun_formula = (
        "((EMA(5) > EMA(20) and EMA(20) > EMA(60) and (EMA(20) - EMA(20,-1)) / EMA(20,-1) > 0) * 25 + "
        "(ATR(14) / Close * 100 >= 5) * 15 + "
        "((ATR(14) / Close * 100 >= 1 and ATR(14) / Close * 100 < 5)) * 10 + "
        "(Vol(0) >= MA(Vol,20) * 2) * 15 + "
        "(Vol(0) >= MA(Vol,20) * 1.1) * 10 + "
        "(BuyQty_5m / SellQty_5m * 100 >= 120) * 15 + "
        "(BuyQty_5m / SellQty_5m * 100 >= 105) * 10 + "
        "((EMA(5,-1) < EMA(20,-1)) and (EMA(5) > EMA(20))) * 5 + "
        "(RSI(14) < 30) * 5 + "
        "((RSI(14) >= 30 and RSI(14) < 40)) * 3) >= 45"
    )
    row = pd.Series({
        "close": 10,
        "open": 10,
        "high": 10,
        "low": 10,
        "volume": 100,
        "BuyQty_5m": 50,
        "SellQty_5m": 0.0,
    })
    result = eval_formula(hyun_formula, row)
    assert isinstance(result, bool)


@pytest.mark.skipif(not pandas_available, reason="pandas not available")
def test_f2_signal_requires_min_rows():
    df = pd.DataFrame({
        "timestamp": pd.date_range("2021-01-01", periods=10, freq="T"),
        "open": np.linspace(1, 10, 10),
        "high": np.linspace(1, 10, 10),
        "low": np.linspace(1, 10, 10),
        "close": np.linspace(1, 10, 10),
        "volume": np.full(10, 100),
    })
    result = f2_signal(df, df, symbol="SYNC_FAIL")
    assert not result["buy_signal"]


@pytest.mark.skipif(not pandas_available, reason="pandas not available")
def test_f2_signal_handles_basic_df(monkeypatch):
    df = pd.DataFrame({
        "timestamp": pd.date_range("2021-01-01 00:00", periods=35, freq="T"),
        "open": np.linspace(1, 35, 35),
        "high": np.linspace(1.1, 35.1, 35),
        "low": np.linspace(0.9, 34.9, 35),
        "close": np.linspace(1, 35, 35),
        "volume": np.full(35, 100),
    })
    result = f2_signal(df, df, symbol="PART")
    assert {"symbol", "buy_signal", "sell_signal"} <= result.keys()


@pytest.mark.skipif(not pandas_available, reason="pandas not available")
def test_f2_signal_accepts_tzaware():
    tz_series = pd.date_range("2021-01-01", periods=35, freq="T", tz="Asia/Seoul")
    df = pd.DataFrame({
        "timestamp": tz_series,
        "open": np.linspace(1, 35, 35),
        "high": np.linspace(1.1, 35.1, 35),
        "low": np.linspace(0.9, 34.9, 35),
        "close": np.linspace(1, 35, 35),
        "volume": np.full(35, 100),
    })
    result = f2_signal(df, df, symbol="TZAWARE")
    assert {"symbol", "buy_signal", "sell_signal"} <= result.keys()


@pytest.mark.skipif(not pandas_available, reason="pandas not available")
def test_eval_formula_with_entry_and_peak():
    row = pd.Series({
        "close": 110,
        "open": 110,
        "high": 110,
        "low": 110,
        "volume": 1,
        "EMA_5": 100,
        "EMA_20": 90,
        "RSI_14": 70,
    })
    formula = (
        "Close >= Entry * 1.015 or Close <= Peak * 0.992 or "
        "Close <= Entry * 0.993 or RSI(14) < 60 or EMA(5) < EMA(20)"
    )
    res = eval_formula(formula, row, entry=100, peak=110)
    assert res


@pytest.mark.skipif(not pandas_available, reason="pandas not available")
def test_f2_signal_strategy_codes_ignored():
    df = pd.DataFrame({
        "timestamp": pd.date_range("2021-01-01", periods=35, freq="T"),
        "open": np.linspace(1, 35, 35),
        "high": np.linspace(1.1, 35.1, 35),
        "low": np.linspace(0.9, 34.9, 35),
        "close": np.linspace(1, 35, 35),
        "volume": np.full(35, 100),
    })
    result = f2_signal(df, df, symbol="FILTER", strategy_codes=["B"])
    assert "buy_signal" in result
