import os
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import threading
from f3_order.position_manager import PositionManager
from f3_order.kpi_guard import KPIGuard
from f3_order.exception_handler import ExceptionHandler

class DummyClient:
    def place_order(self, *args, **kwargs):
        return {"uuid": "1", "state": "wait"}

    def get_accounts(self):
        return []

    def ticker(self, markets):
        return []


def make_pm(tmp_path, monkeypatch):
    monkeypatch.setattr("f3_order.position_manager.UpbitClient", lambda: DummyClient())
    cfg = {
        "DB_PATH": os.path.join(tmp_path, "orders.db"),
        "POSITIONS_FILE": os.path.join(tmp_path, "pos.json"),
        "SELL_LIST_PATH": os.path.join(tmp_path, "sell.json"),
        "TP_PCT": 1.0,
        "PYR_ENABLED": False,
        "AVG_ENABLED": False,
    }
    return PositionManager(cfg, KPIGuard({}), ExceptionHandler({"SLIP_MAX": 0.15}))


def test_schedule_uses_timer(monkeypatch, tmp_path):
    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
    called = []

    class DummyTimer:
        def __init__(self, delay, func, args=None):
            called.append(delay)
        def start(self):
            pass

    monkeypatch.setattr(threading, "Timer", DummyTimer)
    pm = make_pm(tmp_path, monkeypatch)
    pm.open_position({"symbol": "KRW-AAA", "price": 10.0, "qty": 1.0})
    assert called and called[0] == 1

