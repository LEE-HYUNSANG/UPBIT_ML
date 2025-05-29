import importlib.util
import pytest

try:
    import pandas as pd
except Exception:
    pandas_available = False
else:
    pandas_available = True
    import numpy as np
    from pathlib import Path

    spec = importlib.util.spec_from_file_location(
        "data_cleaning", Path(__file__).resolve().parents[1] / "f5_ml_pipeline" / "02_data_cleaning.py"
    )
    data_cleaning = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(data_cleaning)


@pytest.mark.skipif(not pandas_available, reason="pandas not available")
def test_clean_missing_ohlc(tmp_path):
    df = pd.DataFrame({
        "timestamp": pd.date_range("2021-01-01", periods=3, freq="T"),
        "price": [1, 2, 3],
    })
    src = tmp_path / "src.csv"
    df.to_csv(src, index=False)
    dst = tmp_path / "out.parquet"
    data_cleaning.clean_one_file(src, dst, True)
    assert dst.exists() or dst.with_suffix(".csv").exists()
