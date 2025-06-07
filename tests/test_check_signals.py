import importlib
import csv
from pathlib import Path

def test_check_signals_reads_latest(tmp_path, monkeypatch):
    mod = importlib.import_module("f2_buy_signal.check_signals")
    pred_dir = tmp_path / "08_pred"
    pred_dir.mkdir()
    file = pred_dir / "AAA_pred.csv"
    with open(file, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["timestamp", "signal1", "signal2", "signal3"])
        writer.writeheader()
        writer.writerow({"timestamp": "t1", "signal1": 0, "signal2": 0, "signal3": 1})
        writer.writerow({"timestamp": "t2", "signal1": 1, "signal2": 0, "signal3": 1})
    monkeypatch.setattr(mod, "PRED_DIR", pred_dir)
    res = mod.check_signals("AAA")
    assert res == {"signal1": True, "signal2": False, "signal3": True}
