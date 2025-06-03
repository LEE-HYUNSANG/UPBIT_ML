import os
import json
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from f3_order import order_executor as oe

class DummyPM:
    def __init__(self, *_, **__):
        self.positions = []


def test_update_realtime_sell_list_adds_to_empty(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    cfg_dir = tmp_path / "config"
    cfg_dir.mkdir()
    (cfg_dir / "f2_f2_realtime_buy_list.json").write_text("[]")
    (cfg_dir / "f3_f3_realtime_sell_list.json").write_text("[]")

    monkeypatch.setattr(oe, "load_config", lambda p='': {})
    monkeypatch.setattr(oe, "load_buy_config", lambda p=None: {})
    monkeypatch.setattr(oe, "load_sell_config", lambda p=None: {})
    monkeypatch.setattr(oe, "PositionManager", DummyPM)

    executor = oe.OrderExecutor(risk_manager=None)
    executor._update_realtime_sell_list("KRW-BTC")

    with open(cfg_dir / "f3_f3_realtime_sell_list.json", "r", encoding="utf-8") as f:
        data = json.load(f)
    assert data == ["KRW-BTC"]
