import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from f3_order.order_executor import OrderExecutor

class DummyPM:
    def __init__(self, *_, **__):
        pass
    def open_position(self, order_result, status="open"):
        self.last = order_result

def test_entry_sends_alert(monkeypatch):
    monkeypatch.setattr("f3_order.order_executor.load_config", lambda p: {})
    monkeypatch.setattr("f3_order.order_executor.PositionManager", DummyPM)
    monkeypatch.setattr(
        "f3_order.order_executor.smart_buy",
        lambda s, c, position_manager, logger: {
            "filled": True,
            "symbol": s["symbol"],
            "price": 10.0,
            "qty": 1.0,
        },
    )
    oe = OrderExecutor(risk_manager=None)
    calls = []
    oe.exception_handler.send_alert = lambda m, s="info", *a: calls.append((m, s))
    oe.entry({"symbol": "KRW-BTC", "buy_signal": True, "price": 10.0})
    assert len(calls) == 2
    assert "매수 시그널" in calls[0][0]
    assert "BTC" in calls[1][0]
    assert "매수 주문 성공" in calls[1][0]
