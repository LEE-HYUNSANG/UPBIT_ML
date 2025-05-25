import importlib
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
    assert eval_formula("Close > EMA(5) and Vol(0) >= MA(Vol,20)", row)

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
    assert {"symbol", "buy_signal", "sell_signal", "buy_triggers", "sell_triggers"} <= result.keys()
