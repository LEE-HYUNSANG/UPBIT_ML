import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from f3_order.position_manager import PositionManager
from f3_order.kpi_guard import KPIGuard
from f3_order.exception_handler import ExceptionHandler

class DummyClient:
    def __init__(self, recorder):
        self.recorder = recorder
    def place_order(self, *args, **kwargs):
        self.recorder['price'] = kwargs.get('price')
        return {"uuid": "1", "state": "wait"}
    def get_accounts(self):
        return []
    def ticker(self, markets):
        return []


def make_pm(tmp_path, monkeypatch, recorder):
    monkeypatch.setattr("f3_order.position_manager.UpbitClient", lambda: DummyClient(recorder))
    cfg = {
        "DB_PATH": os.path.join(tmp_path, "orders.db"),
        "POSITIONS_FILE": os.path.join(tmp_path, "pos.json"),
        "SELL_LIST_PATH": os.path.join(tmp_path, "sell.json"),
        "TP_PCT": 0.01,
        "PYR_ENABLED": False,
        "AVG_ENABLED": False,
    }
    return PositionManager(cfg, KPIGuard({}), ExceptionHandler({"SLIP_MAX": 0.15}))


def test_tp_price_min_two_ticks(monkeypatch, tmp_path):
    rec = {}
    pm = make_pm(tmp_path, monkeypatch, rec)
    pm.place_tp_order({"symbol": "KRW-AAA", "entry_price": 100.0, "qty": 1.0})
    assert rec.get("price") == 102.0
