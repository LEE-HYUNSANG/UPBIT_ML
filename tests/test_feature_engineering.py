import os
import sys
import pytest
import importlib.util
try:
    import pandas as pd
except Exception:
    pandas_available = False
else:
    pandas_available = True

if pandas_available:
    MODULE_PATH = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "f5_ml_pipeline", "03_feature_engineering.py")
    )
    spec = importlib.util.spec_from_file_location("feature_engineering", MODULE_PATH)
    feature_engineering = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(feature_engineering)
else:  # pragma: no cover - pandas missing
    feature_engineering = None


@pytest.mark.skipif(not pandas_available, reason="pandas not available")
def test_add_features_basic():
    data = {
        "timestamp": pd.date_range("2021-01-01", periods=30, freq="1min"),
        "open": range(30),
        "high": [x + 1 for x in range(30)],
        "low": range(30),
        "close": range(30),
        "volume": [1] * 30,
    }
    df = pd.DataFrame(data)
    result = feature_engineering.add_features(df)
    for col in ["ema5", "ema20", "rsi14", "atr14", "vol_ratio", "stoch_k"]:
        assert col in result.columns
    assert "ma_vol20" not in result.columns
