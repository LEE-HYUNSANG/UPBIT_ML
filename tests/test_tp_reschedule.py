import os
import sys
import threading
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from f3_order.position_manager import PositionManager
from f3_order.kpi_guard import KPIGuard
from f3_order.exception_handler import ExceptionHandler

class DummyClient:
    def place_order(self, *args, **kwargs):
        return {"uuid": "1", "state": "done"}

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
        "PYR_ENABLED": True,
        "PYR_MAX_COUNT": 1,
        "PYR_TRIGGER": 0.0,
        "PYR_SIZE": 100.0,
        "AVG_ENABLED": False,
    }
    return PositionManager(cfg, KPIGuard({}), ExceptionHandler({"SLIP_MAX": 0.15}))

def test_pyramid_reschedules_tp(monkeypatch, tmp_path):
    calls = {"timer": 0, "cancel": 0}

    class DummyTimer:
        def __init__(self, delay, func, args=None):
            calls["timer"] += 1
        def start(self):
            pass

    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
    monkeypatch.setattr(threading, "Timer", DummyTimer)

    pm = make_pm(tmp_path, monkeypatch)
    pm.open_position({"symbol": "KRW-AAA", "price": 100.0, "qty": 1.0})
    pos = pm.positions[0]
    pos["current_price"] = 100.0
    pm.tp_orders[pos["symbol"]] = "old"

    def cancel(sym):
        calls["cancel"] += 1
    monkeypatch.setattr(pm, "cancel_tp_order", cancel)

    pm.process_pyramiding(pos)

    assert calls["cancel"] == 1
    assert calls["timer"] == 2
