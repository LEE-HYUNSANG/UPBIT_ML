import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from f3_order.upbit_api import UpbitClient


def test_market_buy_converts_to_price(monkeypatch):
    captured = {}

    def fake_post(self, path, params=None):
        captured['path'] = path
        captured['params'] = params
        return {'uuid': '1', 'state': 'done'}

    monkeypatch.setattr(UpbitClient, 'post', fake_post, raising=False)

    client = UpbitClient('a', 'b')
    client.place_order('KRW-XRP', 'bid', 1.0, 100.0, 'market')

    assert captured['params']['ord_type'] == 'price'
    assert captured['params']['price'] == '100.0'
    assert 'volume' not in captured['params']


def test_price_order_uses_amount(monkeypatch):
    captured = {}

    def fake_post(self, path, params=None):
        captured['params'] = params
        return {'uuid': '1', 'state': 'done'}

    monkeypatch.setattr(UpbitClient, 'post', fake_post, raising=False)

    client = UpbitClient('a', 'b')
    client.place_order('KRW-XRP', 'bid', 2.0, 50.0, 'price')

    assert captured['params']['ord_type'] == 'price'
    assert captured['params']['price'] == '100.0'
    assert 'volume' not in captured['params']
