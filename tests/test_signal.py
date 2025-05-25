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
    from f2_signal import eval_formula, f2_signal

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
def test_eval_formula_numeric_comparison():
    row = pd.Series({"close": 10, "EMA_5": 9})
    res = eval_formula("Close > EMA(5)", row)
    logging.info(f"[F2_TEST] FORMULA_COMPARE | result={res}")
    assert res

