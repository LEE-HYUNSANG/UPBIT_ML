import importlib
import json
import app


def reload_app():
    importlib.reload(app)
    return app


def load_signals():
    with open(app.MARKET_FILE, encoding="utf-8") as f:
        return json.load(f)


def test_no_filters_returns_all():
    reload_app()
    app.filter_config = {"min_price": 0, "max_price": 0, "rank": 0}
    result = app.get_filtered_signals()
    assert coins == ["BTC", "ETH", "ADA", "SOL"]


def test_min_price_filter():
    reload_app()
    app.filter_config = {"min_price": 1000, "max_price": 0, "rank": 0}
    result = app.get_filtered_signals()
    coins = [r["coin"] for r in result]
    assert coins == ["BTC", "ETH", "ADA", "SOL"]


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
