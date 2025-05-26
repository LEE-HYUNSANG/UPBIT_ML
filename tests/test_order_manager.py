import os
import sqlite3
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from f3_order.position_manager import PositionManager
from f3_order.kpi_guard import KPIGuard
from f3_order.exception_handler import ExceptionHandler
from f3_order.upbit_api import UpbitClient


def make_pm(tmp_path, monkeypatch=None):
    cfg = {
        "DB_PATH": os.path.join(tmp_path, "orders.db"),
        "TP_PCT": 1.0,
        "SL_PCT": 1.0,
        "PYR_ENABLED": False,
        "AVG_ENABLED": False,
    }
    dyn = {}
    guard = KPIGuard({})
    handler = ExceptionHandler({"SLIP_MAX": 0.15})
    if monkeypatch is not None:
        class DummyClient:
            def place_order(self, *args, **kwargs):
                return {
                    "uuid": "1",
                    "state": "done",
                    "side": kwargs.get("side"),
                    "volume": kwargs.get("volume"),
                }

        monkeypatch.setattr("f3_order.position_manager.UpbitClient", lambda: DummyClient())
    return PositionManager(cfg, dyn, guard, handler)


def test_execute_sell_closes_position(tmp_path, monkeypatch):
    pm = make_pm(tmp_path, monkeypatch)
    order = {"symbol": "KRW-BTC", "price": 100.0, "qty": 1.0}
    pm.open_position(order)
    pm.positions[0]["current_price"] = 101.0
    pm.execute_sell(pm.positions[0], "take_profit")
    assert pm.positions[0]["status"] == "closed"
    conn = sqlite3.connect(os.path.join(tmp_path, "orders.db"))
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM orders")
    assert cur.fetchone()[0] == 1
    conn.close()


def test_slippage_handling(tmp_path, monkeypatch):
    pm = make_pm(tmp_path, monkeypatch)
    order = {"symbol": "KRW-BTC", "price": 100.0, "qty": 1.0}
    pm.open_position(order)
    info = {"slippage_pct": 0.2}
    pm.exception_handler.handle_slippage("KRW-BTC", info)
    assert pm.exception_handler.slippage_count["KRW-BTC"] == 1


def test_update_position_from_fill(tmp_path, monkeypatch):
    pm = make_pm(tmp_path, monkeypatch)
    order = {"symbol": "KRW-BTC", "price": 100.0, "qty": 1.0}
    pm.open_position(order)
    fill = {
        "market": "KRW-BTC",
        "side": "ask",
        "volume": "1.0",
        "price": "101.0",
    }
    pm.update_position_from_fill("1", fill)
    assert pm.positions[0]["status"] == "closed"


def test_place_order_partial_fill(tmp_path, monkeypatch):
    class PartialFillClient:
        def place_order(self, *args, **kwargs):
            return {
                "uuid": "2",
                "state": "wait",
                "side": kwargs.get("side"),
                "market": kwargs.get("market"),
                "volume": kwargs.get("volume"),
                "remaining_volume": "1.0",
                "executed_volume": "1.0",
                "price": kwargs.get("price"),
            }

    monkeypatch.setattr("f3_order.position_manager.UpbitClient", lambda: PartialFillClient())
    pm = make_pm(tmp_path)
    order = {"symbol": "KRW-BTC", "price": 100.0, "qty": 2.0}
    pm.open_position(order)
    pm.place_order("KRW-BTC", "sell", 2.0, "market", 100.0)
    assert pm.positions[0]["qty"] == 1.0
    assert pm.positions[0]["status"] == "open"

