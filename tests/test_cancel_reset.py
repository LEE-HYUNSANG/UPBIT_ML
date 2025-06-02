import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from f3_order.order_executor import OrderExecutor
import f3_order.smart_buy as sb
import types

class DummyClient:
    def __init__(self):
        self.canceled = False
    def order_info(self, uuid):
        return {"state": "wait"}
    def cancel_order(self, uuid):
        self.canceled = True

class DummyPM:
    def __init__(self, *_, **__):
        self.positions = []
        self.reset_called = []
        self.client = DummyClient()
    def place_order(self, *a, **k):
        return {"uuid": "1", "price": 10.0, "qty": 1.0}
    def open_position(self, order_result, status="open"):
        order_result["status"] = status
        self.positions.append(order_result)
    def has_position(self, symbol):
        return False
    def _reset_buy_count(self, symbol):
        self.reset_called.append(symbol)


def test_cancel_resets_buy_count(monkeypatch):
    monkeypatch.setattr("f3_order.order_executor.load_config", lambda p: {"LIMIT_WAIT_SEC": 0})
    pm = DummyPM()
    monkeypatch.setattr("f3_order.order_executor.PositionManager", lambda *a, **k: pm)
    monkeypatch.setattr(sb, "time", types.SimpleNamespace(sleep=lambda s: None))
    import importlib
    import f3_order.order_executor as oe_mod
    monkeypatch.setattr(oe_mod, "smart_buy", sb.smart_buy)
    oe = OrderExecutor(risk_manager=None)
    oe.entry({"symbol": "KRW-WAVES", "buy_signal": True, "price": 10.0})
    assert pm.client.canceled
    assert pm.reset_called == ["KRW-WAVES"]
    assert pm.positions == []
