import os
import sys
import json
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
    MODULE_PATH = Path(__file__).resolve().parents[1] / "f5_ml_pipeline" / "09_backtest.py"
    spec = importlib.util.spec_from_file_location("backtest", MODULE_PATH)
    backtest = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(backtest)
else:  # pragma: no cover - pandas missing
    backtest = None


@pytest.mark.skipif(not pandas_available, reason="pandas not available")
def test_process_symbol_merges(tmp_path):
    pred_dir = tmp_path / "08_pred"
    label_dir = tmp_path / "04_label"
    out_dir = tmp_path / "09_backtest"
    pred_dir.mkdir()
    label_dir.mkdir()
    params = {
        "thresh_pct": 0.01,
        "loss_pct": 0.01,
        "trail_start_pct": 0.005,
        "trail_down_pct": 0.003,
    }
    pred_df = pd.DataFrame({
        "timestamp": ["2021-01-01 00:00:00+00:00"],
        "close": [100.0],
        "buy_signal": [1],
    })
    label_df = pd.DataFrame({
        "timestamp": [pd.Timestamp("2021-01-01 00:00:00", tz="UTC")],
        "label": [1],
    })
    pred_df.to_csv(pred_dir / "AAA_pred.csv", index=False)
    label_df.to_parquet(label_dir / "AAA_label.parquet")
    with open(label_dir / "AAA_best_params.json", "w", encoding="utf-8") as f:
        json.dump(params, f)

    backtest.PRED_DIR = pred_dir
    backtest.LABEL_DIR = label_dir
    backtest.OUT_DIR = out_dir
    backtest.LOG_PATH = tmp_path / "log.log"
    backtest.setup_logger()

    backtest.process_symbol("AAA")

    assert (out_dir / "AAA_trades.csv").exists()
