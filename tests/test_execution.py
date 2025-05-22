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
        return {"price": 100.0, "volume": amount / 100.0, "uuid": "m"}

    def buy_limit_order(self, ticker, price, volume):
        self.limit_buy_called += 1
        return {"status": "done", "price": price, "volume": volume, "uuid": "l"}

    def sell_market_order(self, ticker, volume):
        self.market_sell_called += 1
        return {"price": 100.0, "volume": volume, "uuid": "sm"}

    def sell_limit_order(self, ticker, price, volume):
        self.limit_sell_called += 1
        return {"status": "done", "price": price, "volume": volume, "uuid": "sl"}


def _mock_orderbook(ask=100.0, bid=99.0):
    return [{"orderbook_units": [{"ask_price": ask, "bid_price": bid}]}]


def test_smart_buy_market():
    upbit = DummyUpbit()
    with patch(
        "helpers.execution.pyupbit.get_orderbook",
        return_value=_mock_orderbook(ask=100, bid=99.95),
    ), patch(
        "helpers.execution.pyupbit.get_order",
        return_value={"state": "done", "remaining": "0", "executed_volume": 0.1},
    ):
        price, qty = exe.smart_buy(upbit, "KRW-TEST", 10000)
    assert upbit.market_buy_called == 1
    assert price == 100
    assert round(qty, 4) == 0.1


def test_smart_sell_partial():
    upbit = DummyUpbit()
    with patch(
        "helpers.execution.pyupbit.get_orderbook",
        return_value=_mock_orderbook(ask=100, bid=99),
    ), patch(
        "helpers.execution.pyupbit.get_order",
        return_value={"state": "done", "remaining": "0", "executed_volume": 0.1},
    ):
        price, qty = exe.smart_sell(upbit, "KRW-TEST", 0.2)
    assert upbit.market_sell_called == 1
    assert upbit.limit_sell_called == 1
    assert round(price, 1) == 102.0
    assert qty == 0.2


def test_smart_buy_slippage_guard():
    upbit = DummyUpbit()
    with patch(
        "helpers.execution.pyupbit.get_orderbook",
        return_value=_mock_orderbook(ask=100, bid=90),
    ), patch(
        "helpers.execution.pyupbit.get_order",
        return_value={"state": "done", "remaining": "0", "executed_volume": 0.1},
    ):
        price, qty = exe.smart_buy(upbit, "KRW-TEST", 10000, slippage_limit=0.01)
    assert upbit.limit_buy_called == 1
    assert price == 100 - exe.ask_tick(100)
    assert round(qty, 4) == round(10000 / price, 4)


def test_smart_sell_slippage_guard():
    upbit = DummyUpbit()
    with patch(
        "helpers.execution.pyupbit.get_orderbook",
        return_value=_mock_orderbook(ask=200, bid=150),
    ), patch(
        "helpers.execution.pyupbit.get_order",
        return_value={"state": "done", "remaining": "0", "executed_volume": 0.25},
    ):
        price, qty = exe.smart_sell(upbit, "KRW-TEST", 0.5, slippage_limit=0.2)
    assert upbit.market_sell_called == 1
    assert upbit.limit_sell_called == 1
    assert round(price, 1) > 0
    assert qty == 0.5
