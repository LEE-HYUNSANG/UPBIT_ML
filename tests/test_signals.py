import importlib
import app


def reload_app():
    importlib.reload(app)
    return app

def test_filtering():
    reload_app()
    app.market_cache = [
        {"coin": "BTC", "price": 40000, "volume": 1000, "rank": 1, "trend": "", "volatility": "", "strength": "", "gc": "", "rsi": "", "signal": "관망", "signal_class": "wait", "key": "MBREAK"},
        {"coin": "XRP", "price": 500, "volume": 800, "rank": 2, "trend": "", "volatility": "", "strength": "", "gc": "", "rsi": "", "signal": "관망", "signal_class": "wait", "key": "MBREAK"},
        {"coin": "DOGE", "price": 100, "volume": 600, "rank": 3, "trend": "", "volatility": "", "strength": "", "gc": "", "rsi": "", "signal": "관망", "signal_class": "wait", "key": "MBREAK"},
    ]
    app.filter_config = {"min_price": 200, "max_price": 0, "rank": 2}
    signals = app.get_filtered_signals()
    coins = [s["coin"] for s in signals]
    assert coins == ["BTC", "XRP"]
    tickers = app.get_filtered_tickers()
    assert tickers == ["KRW-BTC", "KRW-XRP"]

