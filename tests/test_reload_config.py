import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from f3_order.order_executor import OrderExecutor


class DummyPM:
    def __init__(self, *_, **__):
        pass
    def open_position(self, order_result, status="open"):
        pass


def test_entry_reloads_config(monkeypatch):
    def load_buy(path):
        return {"ENTRY_SIZE_INITIAL": 1}

    def load_buy_new(path):
        return {"ENTRY_SIZE_INITIAL": 2}

    monkeypatch.setattr("f3_order.order_executor.load_config", lambda p: {})
    monkeypatch.setattr("f3_order.order_executor.load_sell_config", lambda p: {})
    monkeypatch.setattr("f3_order.order_executor.load_buy_config", load_buy)
    monkeypatch.setattr("f3_order.order_executor.PositionManager", DummyPM)
    monkeypatch.setattr(
        "f3_order.order_executor.smart_buy",
        lambda s, c, pm, lg: {"filled": True, "symbol": s["symbol"], "price": 10.0, "qty": 1.0},
    )

    oe = OrderExecutor(risk_manager=None)
    assert oe.config["ENTRY_SIZE_INITIAL"] == 1

    monkeypatch.setattr("f3_order.order_executor.load_buy_config", load_buy_new)
    oe.entry({"symbol": "KRW-BTC", "buy_signal": True, "price": 10.0})
    assert oe.config["ENTRY_SIZE_INITIAL"] == 2

