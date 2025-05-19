import importlib
import time
import app

sample_data = [
    {"coin": "BTC", "price": 40000000, "rank": 1, "trend": "", "volatility": "", "volume": "", "strength": "", "gc": "", "rsi": "", "signal": "", "signal_class": "", "key": "MBREAK"},
    {"coin": "ETH", "price": 2500000, "rank": 2, "trend": "", "volatility": "", "volume": "", "strength": "", "gc": "", "rsi": "", "signal": "", "signal_class": "", "key": "MBREAK"},
    {"coin": "XRP", "price": 600, "rank": 5, "trend": "", "volatility": "", "volume": "", "strength": "", "gc": "", "rsi": "", "signal": "", "signal_class": "", "key": "MBREAK"},
]


def reload_app():
    importlib.reload(app)
    app.market_signals = sample_data
    app.market_updated = time.time()
    return app


def test_no_filters_returns_all():
    reload_app()
    app.filter_config = {"min_price": 0, "max_price": 0, "rank": 0}
    result = app.get_filtered_signals()
    assert len(result) == len(sample_data)


def test_min_price_filter():
    reload_app()
    app.filter_config = {"min_price": 1000, "max_price": 0, "rank": 0}
    result = app.get_filtered_signals()
    coins = [r["coin"] for r in result]
    assert coins == ["BTC", "ETH"]


def test_rank_filter():
    reload_app()
    app.filter_config = {"min_price": 0, "max_price": 0, "rank": 3}
    result = app.get_filtered_signals()
    coins = [r["coin"] for r in result]
    assert coins == ["BTC", "ETH"]


def test_filtered_tickers_no_filters():
    reload_app()
    app.filter_config = {"min_price": 0, "max_price": 0, "rank": 0}
    tickers = app.get_filtered_tickers()
    assert tickers == app.config_data.get("tickers")


def test_filtered_tickers_min_price():
    reload_app()
    app.filter_config = {"min_price": 1000, "max_price": 0, "rank": 0}
    tickers = app.get_filtered_tickers()
    assert tickers == ["KRW-BTC", "KRW-ETH", "KRW-ADA"]
