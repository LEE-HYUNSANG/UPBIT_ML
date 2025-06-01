import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from f3_order.order_executor import OrderExecutor

class DummyPM:
    def __init__(self, *_, **__):
        self.positions = []
    def open_position(self, order_result, status="open"):
        order_result["status"] = status
        self.positions.append(order_result)
    def has_position(self, symbol):
        return any(
            p.get("symbol") == symbol and p.get("status") in ("open", "pending")
            for p in self.positions
        )


def test_duplicate_buy_skipped(monkeypatch):
    monkeypatch.setattr("f3_order.order_executor.load_config", lambda p: {"ENTRY_SIZE_INITIAL": 1})
    monkeypatch.setattr("f3_order.order_executor.PositionManager", DummyPM)
    monkeypatch.setattr(
        "f3_order.order_executor.smart_buy",
        lambda s, c, position_manager, logger: {
            "filled": False,
            "symbol": s["symbol"],
            "price": 10.0,
            "qty": 1.0,
        },
    )
    oe = OrderExecutor(risk_manager=None)
    oe.entry({"symbol": "KRW-BTC", "buy_signal": True, "price": 10.0})
    assert len(oe.position_manager.positions) == 1
    oe.entry({"symbol": "KRW-BTC", "buy_signal": True, "price": 10.0})
    assert len(oe.position_manager.positions) == 1


def test_pending_buy_skipped(monkeypatch):
    import threading, time

    monkeypatch.setattr("f3_order.order_executor.load_config", lambda p: {"ENTRY_SIZE_INITIAL": 1})
    monkeypatch.setattr("f3_order.order_executor.PositionManager", DummyPM)

    def slow_buy(s, c, position_manager, logger):
        time.sleep(0.1)
        return {"filled": True, "symbol": s["symbol"], "price": 10.0, "qty": 1.0}

    monkeypatch.setattr("f3_order.order_executor.smart_buy", slow_buy)

    oe = OrderExecutor(risk_manager=None)

    t = threading.Thread(target=oe.entry, args=({"symbol": "KRW-BTC", "buy_signal": True, "price": 10.0},))
    t.start()
    time.sleep(0.02)
    oe.entry({"symbol": "KRW-BTC", "buy_signal": True, "price": 10.0})
    t.join()

    assert len(oe.position_manager.positions) == 1
