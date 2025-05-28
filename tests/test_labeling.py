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
    result = labeling.make_labels(df, horizon=2, thresh_pct=0.003)
    assert list(result["label"]) == [1, -1, 0, 0, 0, 0]
