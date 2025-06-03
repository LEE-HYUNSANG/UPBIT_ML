import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from f3_order.position_manager import PositionManager
from f3_order.kpi_guard import KPIGuard
from f3_order.exception_handler import ExceptionHandler
from f4_riskManager.risk_manager import RiskManager

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
        "TP_PCT": 1.0,
        "POSITIONS_FILE": os.path.join(tmp_path, "pos.json"),
    }
    pm = PositionManager(cfg, KPIGuard({}), ExceptionHandler({"SLIP_MAX": 0.15}))
    return pm


def test_halt_closes_all_positions(tmp_path, monkeypatch):
    pm = make_pm(tmp_path, monkeypatch)
    order = {"symbol": "KRW-BTC", "price": 100.0, "qty": 1.0}
    pm.open_position(order)
    rm = RiskManager(order_executor=type("E", (), {"position_manager": pm})(), exception_handler=ExceptionHandler({}))
    rm.halt("test")
    assert all(p.get("status") == "closed" for p in pm.positions)


def test_hot_reload_updates_config(tmp_path, monkeypatch):
    cfg = os.path.join(tmp_path, "f4_f2_risk_settings.json")
    with open(cfg, "w", encoding="utf-8") as f:
        f.write("{\"DAILY_LOSS_LIM\": 2}")
    class StubExecutor:
        def __init__(self):
            self.config = {}
            self.rm = None

        def update_from_risk_config(self):
            self.config["ENTRY_SIZE_INITIAL"] = self.rm.config.get("ENTRY_SIZE_INITIAL")

    stub = StubExecutor()
    rm = RiskManager(config_path=cfg, order_executor=stub)
    stub.rm = rm
    assert rm.config.get("DAILY_LOSS_LIM") == 2
    with open(cfg, "w", encoding="utf-8") as f:
        f.write("{\"DAILY_LOSS_LIM\": 1, \"ENTRY_SIZE_INITIAL\": 3}")
    rm.hot_reload()
    assert rm.config.get("DAILY_LOSS_LIM") == 1
    assert stub.config.get("ENTRY_SIZE_INITIAL") == 3


def test_disable_symbol_blocks_entry(tmp_path, monkeypatch):
    pm = make_pm(tmp_path, monkeypatch)
    rm = RiskManager(order_executor=type("E", (), {"position_manager": pm})(), exception_handler=ExceptionHandler({}))
    rm.disable_symbol("KRW-BTC")
    assert rm.is_symbol_disabled("KRW-BTC")

