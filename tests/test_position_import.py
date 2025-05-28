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
        return [
            {"currency": "XRP", "balance": "70", "avg_buy_price": "800", "unit_currency": "KRW"},
            {"currency": "ETH", "balance": "0.001", "avg_buy_price": "3400000", "unit_currency": "KRW"},
            {"currency": "KRW", "balance": "100000", "avg_buy_price": "1", "unit_currency": "KRW"},
        ]

    def ticker(self, markets):
        return [{"market": m, "trade_price": 100.0} for m in markets]


def test_import_existing_positions(tmp_path, monkeypatch):
    monkeypatch.setattr("f3_order.position_manager.UpbitClient", lambda: DummyClient())
    cfg = {
        "DB_PATH": os.path.join(tmp_path, "orders.db"),
        "POSITIONS_FILE": os.path.join(tmp_path, "pos.json"),
    }
    pm = PositionManager(cfg, {}, KPIGuard({}), ExceptionHandler({"SLIP_MAX": 0.15}))
    assert len(pm.positions) == 1
    assert pm.positions[0]["symbol"] == "KRW-XRP"
    assert pm.positions[0]["origin"] == "imported"
    assert pm.positions[0]["strategy"] == "imported"
    with open(cfg["POSITIONS_FILE"], "r", encoding="utf-8") as f:
        data = json.load(f)
    assert data and data[0]["strategy"] == "imported"
