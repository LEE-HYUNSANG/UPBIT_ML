import os
import json
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from f3_order.position_manager import PositionManager
from f3_order.kpi_guard import KPIGuard
from f3_order.exception_handler import ExceptionHandler

class DummyClient:
    def place_order(self, *args, **kwargs):
        return {"uuid": "1", "state": "done"}

    def get_accounts(self):
        return [
            {"currency": "XRP", "balance": "70", "avg_buy_price": "800", "unit_currency": "KRW"},
            {"currency": "KRW", "balance": "100000", "avg_buy_price": "1", "unit_currency": "KRW"},
        ]

    def ticker(self, markets):
        return [{"market": m, "trade_price": 100.0} for m in markets]


def test_cleanup_stale_positions(tmp_path, monkeypatch):
    monkeypatch.setattr("f3_order.position_manager.UpbitClient", lambda: DummyClient())
    pos_file = tmp_path / "pos.json"
    with open(pos_file, "w", encoding="utf-8") as f:
        json.dump([
            {"symbol": "KRW-CBK", "status": "open", "entry_price": 700, "qty": 10},
        ], f)
    cfg = {
        "DB_PATH": os.path.join(tmp_path, "orders.db"),
        "POSITIONS_FILE": str(pos_file),
    }
    pm = PositionManager(cfg, KPIGuard({}), ExceptionHandler({"SLIP_MAX": 0.15}))
    assert len(pm.positions) == 1
    assert pm.positions[0]["symbol"] == "KRW-XRP"
    with open(pos_file, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert len(data) == 1 and data[0]["symbol"] == "KRW-XRP"
