import os
import sys
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


def make_pm(tmp_path, monkeypatch):
    monkeypatch.setattr("f3_order.position_manager.UpbitClient", lambda: DummyClient())
    cfg = {
        "DB_PATH": os.path.join(tmp_path, "orders.db"),
        "POSITIONS_FILE": os.path.join(tmp_path, "pos.json"),
    }
    return PositionManager(cfg, {}, KPIGuard({}), ExceptionHandler({"SLIP_MAX": 0.15}))


def test_manage_trailing_stop_missing_entry_price(tmp_path, monkeypatch):
    pm = make_pm(tmp_path, monkeypatch)
    position = {"symbol": "KRW-BTC", "qty": 1.0, "status": "open", "current_price": 100.0}
    pm.manage_trailing_stop(position)
    assert position["status"] == "open"
