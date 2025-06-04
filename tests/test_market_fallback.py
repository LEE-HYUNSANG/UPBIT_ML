import os
import sys
import types
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import f3_order.smart_buy as sb

class DummyPM:
    def __init__(self):
        self.orders = []
        self.client = types.SimpleNamespace(
            order_info=lambda u: {"state": "wait"},
            orderbook=lambda m: [{"orderbook_units": [{"bid_price": 10.0, "ask_price": 10.0}]}],
        )

    def place_order(self, symbol, side, qty, order_type="market", price=None):
        self.orders.append((order_type, price))
        state = "done" if order_type == "market" else "wait"
        return {"uuid": "1", "state": state, "executed_volume": qty if order_type == "market" else 0, "price": price, "qty": qty}
    def _reset_buy_count(self, symbol):
        pass


def test_market_fallback(monkeypatch):
    monkeypatch.setattr(sb, "time", types.SimpleNamespace(sleep=lambda s: None))
    pm = DummyPM()
    config = {"LIMIT_WAIT_SEC_1": 0, "LIMIT_WAIT_SEC_2": 0, "FALLBACK_MARKET": True, "ENTRY_SIZE_INITIAL": 10000}
    res = sb.smart_buy({"symbol": "KRW-AAA", "price": 10.0}, config, position_manager=pm)
    assert res["filled"]
    assert pm.orders[-1][0] == "market"

