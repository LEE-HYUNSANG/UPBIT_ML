import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from f3_order.utils import calc_target_prices
from f3_order.order_executor import OrderExecutor

class DummyPM:
    def __init__(self, *_, **__):
        self.last = None
    def open_position(self, order_result, status="open"):
        self.last = order_result
    def has_position(self, symbol):
        return False


def test_calc_target_prices_rounds():
    entry, tp = calc_target_prices(100.0, 0.33)
    assert entry == 100.0
    assert tp == 101.0


def test_entry_sets_tp_from_predicted_rise(monkeypatch):
    monkeypatch.setattr("f3_order.order_executor.load_config", lambda p: {})
    monkeypatch.setattr("f3_order.order_executor.load_sell_config", lambda p: {})
    monkeypatch.setattr("f3_order.order_executor.PositionManager", DummyPM)
    def dummy_smart_buy(signal, cfg, pm, logger, max_price=None):
        assert max_price == 100.0
        return {"filled": True, "symbol": signal["symbol"], "price": 100.0, "qty": 1.0}
    monkeypatch.setattr("f3_order.order_executor.smart_buy", dummy_smart_buy)
    oe = OrderExecutor(risk_manager=None)
    oe.exception_handler.send_alert = lambda *a, **k: None
    signal = {"symbol": "KRW-BTC", "buy_signal": True, "price": 100.0, "predicted_rise": 0.33}
    oe.entry(signal)
    assert oe.position_manager.last["tp_price"] == 101.0

