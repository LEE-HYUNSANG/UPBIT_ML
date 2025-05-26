import os
import sqlite3
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from f3_order.position_manager import PositionManager
from f3_order.kpi_guard import KPIGuard
from f3_order.exception_handler import ExceptionHandler


def make_pm(tmp_path):
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
    return PositionManager(cfg, dyn, guard, handler)


def test_execute_sell_closes_position(tmp_path):
    pm = make_pm(tmp_path)
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


def test_slippage_handling(tmp_path):
    pm = make_pm(tmp_path)
    order = {"symbol": "KRW-BTC", "price": 100.0, "qty": 1.0}
    pm.open_position(order)
    info = {"slippage_pct": 0.2}
    pm.exception_handler.handle_slippage("KRW-BTC", info)
    assert pm.exception_handler.slippage_count["KRW-BTC"] == 1

