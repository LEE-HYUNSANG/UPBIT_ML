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
    from f2_signal.signal_engine import eval_formula, f2_signal

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
def test_eval_formula_with_offset():
    df = pd.DataFrame({"close": [1, 2, 3], "open": [1, 1, 1]})
    row = df.iloc[2]
    res = eval_formula("Close > Close(-1)", row, data_df=df)
    assert res


@pytest.mark.skipif(not pandas_available, reason="pandas not available")
def test_f2_signal_requires_synced_candles():
    df1 = pd.DataFrame({
        "timestamp": pd.date_range("2021-01-01 00:00", periods=25, freq="T"),
        "open": np.linspace(1, 25, 25),
        "high": np.linspace(1.1, 25.1, 25),
        "low": np.linspace(0.9, 24.9, 25),
        "close": np.linspace(1, 25, 25),
        "volume": np.full(25, 100),
    })
    df5 = pd.DataFrame({
        "timestamp": pd.date_range("2021-01-01 00:00", periods=6, freq="5T"),
        "open": np.linspace(1, 6, 6),
        "high": np.linspace(1.1, 6.1, 6),
        "low": np.linspace(0.9, 5.9, 6),
        "close": np.linspace(1, 6, 6),
        "volume": np.full(6, 100),
    })
    result = f2_signal(df1, df5, symbol="SYNC_FAIL")
    assert not result["buy_signal"] and not result["sell_signal"]


@pytest.mark.skipif(not pandas_available, reason="pandas not available")
def test_f2_signal_handles_partial_candle(monkeypatch):
    now = pd.Timestamp("2021-01-01 00:25:30")
    monkeypatch.setattr(pd.Timestamp, "utcnow", staticmethod(lambda: now))

    df1 = pd.DataFrame({
        "timestamp": pd.date_range("2021-01-01 00:00", periods=27, freq="T"),
        "open": np.linspace(1, 27, 27),
        "high": np.linspace(1.1, 27.1, 27),
        "low": np.linspace(0.9, 26.9, 27),
        "close": np.linspace(1, 27, 27),
        "volume": np.full(27, 100),
    })
    df5 = pd.DataFrame({
        "timestamp": pd.date_range("2021-01-01 00:00", periods=6, freq="5T"),
        "open": np.linspace(1, 6, 6),
        "high": np.linspace(1.1, 6.1, 6),
        "low": np.linspace(0.9, 5.9, 6),
        "close": np.linspace(1, 6, 6),
        "volume": np.full(6, 100),
    })
    result = f2_signal(df1, df5, symbol="PART")
    assert {"symbol", "buy_signal", "sell_signal"} <= result.keys()


@pytest.mark.skipif(not pandas_available, reason="pandas not available")
def test_f2_signal_accepts_tzaware():
    tz_series = pd.date_range("2021-01-01", periods=30, freq="T", tz="Asia/Seoul")
    df1 = pd.DataFrame({
        "timestamp": tz_series,
        "open": np.linspace(1, 30, 30),
        "high": np.linspace(1.1, 30.1, 30),
        "low": np.linspace(0.9, 29.9, 30),
        "close": np.linspace(1, 30, 30),
        "volume": np.full(30, 100),
    })
    df5 = pd.DataFrame({
        "timestamp": tz_series[::5].reset_index(drop=True),
        "open": np.linspace(1, 6, 6),
        "high": np.linspace(1.1, 6.1, 6),
        "low": np.linspace(0.9, 5.9, 6),
        "close": np.linspace(1, 6, 6),
        "volume": np.full(6, 100),
    })
    result = f2_signal(df1, df5, symbol="TZAWARE")
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
def test_f2_signal_strategy_filter(monkeypatch):
    df = pd.DataFrame({
        "timestamp": pd.date_range("2021-01-01", periods=30, freq="T"),
        "open": np.linspace(1, 30, 30),
        "high": np.linspace(1.1, 30.1, 30),
        "low": np.linspace(0.9, 29.9, 30),
        "close": np.linspace(1, 30, 30),
        "volume": np.full(30, 100),
    })
    fake_strats = [
        {"short_code": "A", "buy_formula": "Close > 0", "sell_formula": "Close < 0"},
        {"short_code": "B", "buy_formula": "Close > 0", "sell_formula": "Close < 0"},
    ]
    monkeypatch.setattr("f2_signal.signal_engine.strategies", fake_strats)
    result = f2_signal(df, df, symbol="FILTER", strategy_codes=["B"])
    assert result["buy_triggers"] == ["B"]
