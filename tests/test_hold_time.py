import os
import sys
import time

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
        "HOLD_SECS": 1,
        "TP_PCT": 100,
        "POSITIONS_FILE": os.path.join(tmp_path, "pos.json"),
    }
    return PositionManager(cfg, KPIGuard({}), ExceptionHandler({"SLIP_MAX": 0.15}))


def test_hold_loop_respects_hold_secs(tmp_path, monkeypatch):
    pm = make_pm(tmp_path, monkeypatch)
    pm.open_position({"symbol": "KRW-BTC", "price": 100.0, "qty": 1.0})
    pos = pm.positions[0]
    pos["current_price"] = 100.0
    pos["entry_time"] = time.time() - 2

    calls = {"trail": 0, "pyr": 0, "avg": 0}
    monkeypatch.setattr(pm, "manage_trailing_stop", lambda p: calls.__setitem__("trail", calls["trail"] + 1))
    monkeypatch.setattr(pm, "process_pyramiding", lambda p: calls.__setitem__("pyr", calls["pyr"] + 1))
    monkeypatch.setattr(pm, "process_averaging_down", lambda p: calls.__setitem__("avg", calls["avg"] + 1))

    pm.hold_loop()

    assert calls["trail"] == 1
    assert calls["pyr"] == 0
    assert calls["avg"] == 0

