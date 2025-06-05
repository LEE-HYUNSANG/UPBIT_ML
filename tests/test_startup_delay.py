import os
import sys
import time
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from f3_order.order_executor import OrderExecutor
import f3_order.order_executor as oe

class DummyPM:
    def __init__(self, *_, **__):
        pass
    def open_position(self, order_result, status="open"):
        pass

def test_entry_waits_for_startup(monkeypatch):
    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
    monkeypatch.setattr(oe, "load_config", lambda p=None: {})
    monkeypatch.setattr(oe, "load_sell_config", lambda p=None: {})
    monkeypatch.setattr(oe, "load_buy_config", lambda p=None: {"STARTUP_HOLD_SEC": 10})
    monkeypatch.setattr(oe, "PositionManager", DummyPM)
    monkeypatch.setattr(oe, "smart_buy", lambda s, c, pm, lg: {"filled": True, "symbol": s["symbol"], "price": 10.0, "qty": 1.0})
    monkeypatch.setattr(oe, "_startup_time", time.time())
    oe_inst = OrderExecutor(risk_manager=None)
    result = oe_inst.entry({"symbol": "KRW-BTC", "buy_signal": True, "price": 10.0})
    assert result is False
