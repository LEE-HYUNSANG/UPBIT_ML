import importlib
import sys
import types


def load_app():
    fake = types.SimpleNamespace(
        get_tickers=lambda fiat="KRW": [
            "KRW-BTC",
            "KRW-ETH",
            "KRW-XRP",
            "KRW-DOGE",
        ],
        get_ticker=lambda tickers: [
            {"market": "KRW-BTC", "trade_price": 40000000, "acc_trade_price_24h": 5000},
            {"market": "KRW-ETH", "trade_price": 2500000, "acc_trade_price_24h": 4000},
            {"market": "KRW-XRP", "trade_price": 600, "acc_trade_price_24h": 3000},
            {"market": "KRW-DOGE", "trade_price": 150, "acc_trade_price_24h": 1000},
        ],
    )
    sys.modules['pyupbit'] = fake
    if 'app' in sys.modules:
        importlib.reload(sys.modules['app'])
    else:
        import app
    return sys.modules['app']


def test_no_filters_returns_all():
    app = load_app()
    app.filter_config = {"min_price": 0, "max_price": 0, "rank": 0}
    result = app.get_filtered_signals()
    coins = [r["coin"] for r in result]
    assert coins == ["BTC", "ETH", "XRP", "DOGE"]


def test_min_price_filter():
    app = load_app()
    app.filter_config = {"min_price": 1000, "max_price": 0, "rank": 0}
    result = app.get_filtered_signals()
    coins = [r["coin"] for r in result]
    assert coins == ["BTC", "ETH"]


def test_rank_filter():
    app = load_app()
    app.filter_config = {"min_price": 0, "max_price": 0, "rank": 2}
    result = app.get_filtered_signals()
    coins = [r["coin"] for r in result]
    assert coins == ["BTC", "ETH"]


def test_filtered_tickers_min_price():
    app = load_app()
    app.filter_config = {"min_price": 1000, "max_price": 0, "rank": 0}
    tickers = app.get_filtered_tickers()
    assert tickers == ["KRW-BTC", "KRW-ETH"]
