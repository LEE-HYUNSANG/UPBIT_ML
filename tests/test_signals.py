import sys
import types
import importlib

class StubPyUpbit(types.ModuleType):
    def __init__(self):
        super().__init__("pyupbit")
    def get_tickers(self, fiat="KRW"):
        return ["KRW-BTC", "KRW-ETH", "KRW-XRP", "KRW-DOGE"]
    def get_market_ticker(self, tickers):
        data = {
            "KRW-BTC": {"market": "KRW-BTC", "trade_price": 20000, "acc_trade_price_24h": 50000},
            "KRW-ETH": {"market": "KRW-ETH", "trade_price": 2000, "acc_trade_price_24h": 40000},
            "KRW-XRP": {"market": "KRW-XRP", "trade_price": 600, "acc_trade_price_24h": 30000},
            "KRW-DOGE": {"market": "KRW-DOGE", "trade_price": 150, "acc_trade_price_24h": 1000},
        }
        return [data[t] for t in tickers]
    class Upbit:
        def __init__(self, key, secret):
            pass
        def get_balances(self):
            return []

sys.modules['pyupbit'] = StubPyUpbit()

import app
importlib.reload(app)


def test_filters_work():
    app.market_cache = [
        {"coin": "BTC", "price": 20000, "volume": 50000, "rank": 1},
        {"coin": "ETH", "price": 2000, "volume": 40000, "rank": 2},
        {"coin": "XRP", "price": 600, "volume": 30000, "rank": 3},
        {"coin": "DOGE", "price": 150, "volume": 1000, "rank": 20},
    ]
    app.filter_config = {"min_price": 700, "max_price": 23000, "rank": 20}
    signals = app.get_filtered_signals()
    coins = [s["coin"] for s in signals]
    assert coins == ["ETH", "XRP"]


def test_filtered_tickers():
    app.market_cache = [
        {"coin": "BTC", "price": 20000, "volume": 50000, "rank": 1},
        {"coin": "ETH", "price": 2000, "volume": 40000, "rank": 2},
        {"coin": "XRP", "price": 600, "volume": 30000, "rank": 3},
        {"coin": "DOGE", "price": 150, "volume": 1000, "rank": 20},
    ]
    app.filter_config = {"min_price": 700, "max_price": 0, "rank": 0}
    tickers = app.get_filtered_tickers()
    assert tickers == ["KRW-BTC", "KRW-ETH"]
