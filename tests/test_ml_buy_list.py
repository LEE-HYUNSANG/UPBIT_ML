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
    (cfg / "coin_list_monitoring.json").write_text(json.dumps(["KRW-AAA", "KRW-BBB"]))
    (cfg / "coin_realtime_buy_list.json").write_text(json.dumps({"KRW-AAA": 1}))
    (cfg / "coin_realtime_sell_list.json").write_text(json.dumps({"KRW-AAA": {"SL_PCT": 1}}))
    (cfg / "risk.json").write_text(json.dumps({
        "SL_PCT": 1.0,
        "TP_PCT": 2.0,
        "TRAILING_STOP_ENABLED": True,
        "TRAIL_START_PCT": 0.5,
        "TRAIL_STEP_PCT": 1.0
    }))

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
    monkeypatch.setattr(ml, "check_buy_signal", Dummy(True))

    result = ml.run()
    buy = json.loads((cfg / "coin_realtime_buy_list.json").read_text())
    sell = json.loads((cfg / "coin_realtime_sell_list.json").read_text())

    assert "KRW-BBB" in buy and buy["KRW-BBB"] == 0
    assert "KRW-BBB" in sell
    assert result == ["KRW-AAA", "KRW-BBB"]

