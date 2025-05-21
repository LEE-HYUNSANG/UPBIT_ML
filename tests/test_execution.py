from unittest.mock import patch

import helpers.execution as exe


class DummyUpbit:
    def __init__(self):
        self.market_buy_called = 0
        self.limit_buy_called = 0
        self.market_sell_called = 0
        self.limit_sell_called = 0

    def buy_market_order(self, ticker, amount):
        self.market_buy_called += 1
        return {"price": 100.0, "volume": amount / 100.0}

    def buy_limit_order(self, ticker, price, volume):
        self.limit_buy_called += 1
        return {"status": "done", "price": price, "volume": volume}

    def sell_market_order(self, ticker, volume):
        self.market_sell_called += 1
        return {"price": 100.0, "volume": volume}

    def sell_limit_order(self, ticker, price, volume):
        self.limit_sell_called += 1
        return {"status": "done", "price": price, "volume": volume}


def _mock_orderbook(ask=100.0, bid=99.0):
    return [{"orderbook_units": [{"ask_price": ask, "bid_price": bid}]}]


def test_smart_buy_market():
    upbit = DummyUpbit()
    with patch("helpers.execution.pyupbit.get_orderbook", return_value=_mock_orderbook(ask=100, bid=99.95)):
        price, qty = exe.smart_buy(upbit, "KRW-TEST", 10000, slippage=0.001)
    assert upbit.market_buy_called == 1
    assert price == 100
    assert round(qty, 4) == 0.1


def test_smart_sell_limit():
    upbit = DummyUpbit()
    with patch("helpers.execution.pyupbit.get_orderbook", return_value=_mock_orderbook(ask=100, bid=99)):
        price, qty = exe.smart_sell(upbit, "KRW-TEST", 0.2, slippage=0.0001)
    assert upbit.limit_sell_called == 1
    assert price == 99 + exe._tick_size(99)
    assert qty == 0.2


def test_smart_buy_slippage_guard():
    upbit = DummyUpbit()
    with patch(
        "helpers.execution.pyupbit.get_orderbook",
        return_value=_mock_orderbook(ask=100, bid=90),
    ):
        price, qty = exe.smart_buy(
            upbit,
            "KRW-TEST",
            10000,
            slippage=0.001,
            slippage_limit=0.05,
        )
    assert price == 0
    assert qty == 0
    assert upbit.market_buy_called == 0


def test_smart_sell_slippage_guard():
    upbit = DummyUpbit()
    with patch(
        "helpers.execution.pyupbit.get_orderbook",
        return_value=_mock_orderbook(ask=200, bid=150),
    ):
        price, qty = exe.smart_sell(
            upbit,
            "KRW-TEST",
            0.5,
            slippage=0.001,
            slippage_limit=0.2,
        )
    assert price == 0
    assert qty == 0
    assert upbit.market_sell_called == 0
