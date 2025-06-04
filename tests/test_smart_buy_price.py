import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import f3_order.smart_buy as sb

class DummyClient:
    def orderbook(self, markets):
        return [{"orderbook_units": [{"bid_price": 10.0, "ask_price": 10.5}]}]


def test_bid1_plus_returns_next_tick():
    price = sb._get_price("BID1+", "KRW-AAA", DummyClient())
    assert price == 10.1

