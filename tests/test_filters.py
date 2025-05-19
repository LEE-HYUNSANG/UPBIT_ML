import importlib
import sys
import types

# stub pyupbit module
stub = types.SimpleNamespace(
    get_tickers=lambda fiat="KRW": ["KRW-AAA", "KRW-BBB", "KRW-CCC"],
    get_ticker=lambda tickers: [
        {"market": "KRW-AAA", "trade_price": 1500, "acc_trade_price_24h": 5_000_000},
        {"market": "KRW-BBB", "trade_price": 800, "acc_trade_price_24h": 10_000_000},
        {"market": "KRW-CCC", "trade_price": 20000, "acc_trade_price_24h": 2_000_000},
    ],
)
sys.modules['pyupbit'] = stub

import app


def reload_app():
    importlib.reload(app)
    return app


def test_filtered_tickers_rank_and_price():
    reload_app()
    app.filter_config = {"min_price": 700, "max_price": 23000, "rank": 2}
    with app._market_lock:
        app.market_cache = app.load_market_signals()
    tickers = app.get_filtered_tickers()
    assert tickers == ["KRW-BBB", "KRW-AAA"]
