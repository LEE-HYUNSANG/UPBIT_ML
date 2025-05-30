import json
import os
import sys
import types
from pathlib import Path

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


class Dummy:
    def __init__(self, result):
        self.result = result

    def __call__(self, symbol):
        return self.result


def test_run_updates_buy_and_sell_lists(tmp_path, monkeypatch):
    cfg = tmp_path
    (cfg / "f5_f1_monitoring_list.json").write_text(
        json.dumps([
            {"symbol": "KRW-AAA", "thresh_pct": 0.01, "loss_pct": 0.02},
            {"symbol": "KRW-BBB", "thresh_pct": 0.01, "loss_pct": 0.02},
        ])
    )
    (cfg / "f2_f2_realtime_buy_list.json").write_text("[]")

    # Stub optional dependencies before importing module
    pandas_stub = types.ModuleType("pandas")
    pandas_stub.Series = object
    pandas_stub.DataFrame = object
    sklearn_stub = types.ModuleType("sklearn")
    linear_stub = types.ModuleType("sklearn.linear_model")
    linear_stub.LogisticRegression = object
    joblib_stub = types.ModuleType("joblib")
    joblib_stub.dump = lambda *a, **k: None
    joblib_stub.load = lambda *a, **k: None
    numpy_stub = types.ModuleType("numpy")
    sys.modules.update({
        "pandas": pandas_stub,
        "sklearn": sklearn_stub,
        "sklearn.linear_model": linear_stub,
        "joblib": joblib_stub,
        "numpy": numpy_stub,
        "pyupbit": types.ModuleType("pyupbit"),
    })

    from f2_ml_buy_signal import f2_ml_buy_signal as ml

    monkeypatch.setattr(ml, "CONFIG_DIR", Path(cfg))
    monkeypatch.setattr(ml, "check_buy_signal", Dummy((True, True, True)))

    result = ml.run()
    buy = json.loads((cfg / "f2_f2_realtime_buy_list.json").read_text())

    assert any(b["symbol"] == "KRW-BBB" for b in buy)
    assert result == ["KRW-AAA", "KRW-BBB"]


def test_run_if_monitoring_skips_when_missing(tmp_path, monkeypatch):
    from f2_ml_buy_signal import f2_ml_buy_signal as ml

    monkeypatch.setattr(ml, "CONFIG_DIR", Path(tmp_path))
    called = {"cnt": 0}

    def fake_run():
        called["cnt"] += 1
        return ["OK"]

    monkeypatch.setattr(ml, "run", fake_run)

    result = ml.run_if_monitoring_list_exists()
    assert result == []
    assert called["cnt"] == 0


def test_run_if_monitoring_executes(tmp_path, monkeypatch):
    from f2_ml_buy_signal import f2_ml_buy_signal as ml

    monkeypatch.setattr(ml, "CONFIG_DIR", Path(tmp_path))
    (tmp_path / "f5_f1_monitoring_list.json").write_text("[]")
    called = {"cnt": 0}

    def fake_run():
        called["cnt"] += 1
        return ["OK"]

    monkeypatch.setattr(ml, "run", fake_run)

    result = ml.run_if_monitoring_list_exists()
    assert result == ["OK"]
    assert called["cnt"] == 1

