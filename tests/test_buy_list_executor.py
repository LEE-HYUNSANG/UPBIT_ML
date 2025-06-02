import json
import os
import sys
import types
from pathlib import Path
import importlib

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


class DummyExecutor:
    def __init__(self):
        self.called = []

    def entry(self, signal):
        self.called.append(signal)


class DummyClient:
    def __init__(self, price=10.0):
        self.price = price

    def ticker(self, markets):
        return [{"market": m, "trade_price": self.price} for m in markets]


def test_execute_buy_list(tmp_path, monkeypatch):
    pandas_stub = types.ModuleType("pandas")
    pandas_stub.Series = object
    pandas_stub.DataFrame = object
    monkeypatch.setitem(sys.modules, "pandas", pandas_stub)
    engine_mod = types.ModuleType(
        "f2_ml_buy_signal.03_buy_signal_engine.signal_engine"
    )
    monkeypatch.setitem(
        sys.modules,
        "f2_ml_buy_signal.03_buy_signal_engine.signal_engine",
        engine_mod,
    )

    ble = importlib.import_module("f2_ml_buy_signal.03_buy_signal_engine.buy_list_executor")

    data = [{"symbol": "KRW-BTC", "buy_signal": 1, "buy_count": 0}]
    (tmp_path / "f2_f2_realtime_buy_list.json").write_text(json.dumps(data))

    monkeypatch.setattr(ble, "CONFIG_DIR", Path(tmp_path))
    executor = DummyExecutor()
    monkeypatch.setattr(ble, "_default_executor", executor)
    monkeypatch.setattr(ble, "UpbitClient", lambda: DummyClient(100.0))

    result = ble.execute_buy_list()

    assert result == ["KRW-BTC"]
    assert executor.called
    assert executor.called[0]["price"] == 100.0
    after = json.loads((tmp_path / "f2_f2_realtime_buy_list.json").read_text())
    assert after[0]["buy_count"] == 1
