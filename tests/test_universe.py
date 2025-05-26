import sys
import types
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

if 'requests' not in sys.modules:
    fake_requests = types.SimpleNamespace()
    sys.modules['requests'] = fake_requests

from f1_universe import universe_selector as us


def _make_fake_data(markets):
    ticker_items = []
    orderbook_items = []
    for m in markets:
        ticker_items.append({
            "market": m,
            "trade_price": 100.0,
            "high_price": 110.0,
            "low_price": 90.0,
            "prev_closing_price": 100.0,
        })
        orderbook_items.append({
            "market": m,
            "orderbook_units": [{"ask_price": 101.0, "bid_price": 99.0}],
        })
    return ticker_items, orderbook_items


def test_apply_filters_batches_requests(monkeypatch):
    calls = []

    def fake_fetch_json(url, params=None):
        calls.append(url)
        markets = params.get("markets", "").split(",")
        if url.endswith("/ticker"):
            data, _ = _make_fake_data(markets)
            return data
        elif url.endswith("/orderbook"):
            _, data = _make_fake_data(markets)
            return data
        return []

    monkeypatch.setattr(us, "_fetch_json", fake_fetch_json)

    tickers = [f"KRW-{i:03d}" for i in range(150)]
    cfg = {"max_spread": 1000.0}
    result = us.apply_filters(tickers, cfg)

    # Two calls per 100-ticker chunk: one for ticker and one for orderbook
    assert len(calls) == 4
    assert all(calls[i].endswith(path) for i, path in enumerate(["/ticker", "/orderbook", "/ticker", "/orderbook"]))
    assert len(result) == len(tickers)
