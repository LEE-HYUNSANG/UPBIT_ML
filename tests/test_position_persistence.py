import os
import sys
import json

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from f3_order.position_manager import PositionManager
from f3_order.kpi_guard import KPIGuard
from f3_order.exception_handler import ExceptionHandler

class DummyClient:
    def place_order(self, *args, **kwargs):
        return {"uuid": "1", "state": "done", "side": kwargs.get("side"), "volume": kwargs.get("volume", 0)}

    def get_accounts(self):
        return []

    def ticker(self, markets):
        return [{"market": m, "trade_price": 100.0} for m in markets]


def test_load_positions_from_file(tmp_path, monkeypatch):
    positions_file = tmp_path / "pos.json"
    data = [{
        "symbol": "KRW-BTC",
        "entry_time": 0,
        "entry_price": 1.0,
        "qty": 1.0,
        "status": "open",
        "strategy": "TEST"
    }]
    positions_file.write_text(json.dumps(data))
    monkeypatch.setattr("f3_order.position_manager.UpbitClient", lambda: DummyClient())
    cfg = {"DB_PATH": os.path.join(tmp_path, "orders.db"), "POSITIONS_FILE": str(positions_file)}
    pm = PositionManager(cfg, KPIGuard({}), ExceptionHandler({"SLIP_MAX": 0.15}))
    assert pm.positions == []


def test_refresh_persists_positions(tmp_path, monkeypatch):
    positions_file = tmp_path / "positions.json"
    data = [
        {
            "symbol": "KRW-XRP",
            "entry_time": 0,
            "entry_price": 1.0,
            "qty": 1.0,
            "status": "open",
            "strategy": "TEST",
        }
    ]
    positions_file.write_text(json.dumps(data))
    monkeypatch.setattr("f3_order.position_manager.UpbitClient", lambda: DummyClient())
    cfg = {"DB_PATH": os.path.join(tmp_path, "orders.db"), "POSITIONS_FILE": str(positions_file)}
    pm = PositionManager(cfg, KPIGuard({}), ExceptionHandler({"SLIP_MAX": 0.15}))
    pm.refresh_positions()
    with open(positions_file, "r", encoding="utf-8") as f:
        persisted = json.load(f)
    assert persisted == []
