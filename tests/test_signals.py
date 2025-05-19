import importlib
import app


def reload_app():
    importlib.reload(app)
    return app


def test_no_filters_returns_all():
    reload_app()
    app.filter_config = {"min_price": 0, "max_price": 0, "rank": 0}
    result = app.get_filtered_signals()
    assert len(result) == len(app.sample_signals)


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
