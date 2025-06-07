import importlib.util
from pathlib import Path
import pytest

try:
    import pandas as pd
except Exception:
    pandas_available = False
else:
    pandas_available = True

if pandas_available:
    spec = importlib.util.spec_from_file_location(
        "labeling",
        Path(__file__).resolve().parents[1] / "f5_ml_pipeline" / "04_labeling.py",
    )
    labeling = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(labeling)
else:  # pragma: no cover - pandas missing
    labeling = None


@pytest.mark.skipif(not pandas_available, reason="pandas not available")
def test_make_labels_basic():
    df = pd.DataFrame(
        {
            "timestamp": pd.date_range("2021-01-01", periods=6, freq="T"),
            "open": [100] * 6,
            "high": [100.2, 100.2, 100.4, 100.1, 100.1, 100.1],
            "low": [100, 99, 99.8, 99.9, 99.9, 99.9],
            "close": [100] * 6,
            "volume": [1] * 6,
        }
    )
    result = labeling.make_labels_basic(df, horizon=2, thresh_pct=0.003)
    for col in ["signal1", "signal2", "signal3"]:
        assert col in result.columns


@pytest.mark.skipif(not pandas_available, reason="pandas not available")
def test_trailing_none_uses_basic():
    df = pd.DataFrame(
        {
            "timestamp": pd.date_range("2021-01-01", periods=6, freq="T"),
            "open": [100] * 6,
            "high": [100.2, 100.2, 100.4, 100.1, 100.1, 100.1],
            "low": [100, 99, 99.8, 99.9, 99.9, 99.9],
            "close": [100] * 6,
            "volume": [1] * 6,
        }
    )
    res_trail = labeling.make_labels_trailing(
        df,
        horizon=2,
        thresh_pct=0.003,
        loss_pct=0.003,
        trail_start_pct=None,
        trail_down_pct=None,
    )
    res_basic = labeling.make_labels_basic(df, horizon=2, thresh_pct=0.003)
    assert list(res_trail["label"]) == list(res_basic["label"])


@pytest.mark.skipif(not pandas_available, reason="pandas not available")
def test_make_labels_trailing_multistage():
    df = pd.DataFrame(
        {
            "timestamp": pd.date_range("2021-01-01", periods=6, freq="T"),
            "open": [101, 102, 100, 101, 100, 100],
            "high": [101, 102, 100, 101, 100, 100],
            "low": [101, 102, 100, 101, 100, 100],
            "close": [101, 102, 100, 101, 100, 100],
            "volume": [1] * 6,
        }
    )
    result = labeling.make_labels_trailing(
        df,
        horizon=2,
        thresh_pct=0.01,
        loss_pct=0.01,
        trail_start_pct=0.005,
        trail_down_pct=0.005,
    )
    assert list(result["label"][:4]) == [2, -1, 1, 0]
