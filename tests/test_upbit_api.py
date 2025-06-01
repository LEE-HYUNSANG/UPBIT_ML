import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from f3_order.upbit_api import UpbitClient
import pytest


def test_market_buy_converts_to_price(monkeypatch):
    captured = {}

    def fake_post(self, path, params=None):
        captured['path'] = path
        captured['params'] = params
        return {'uuid': '1', 'state': 'done'}

    monkeypatch.setattr(UpbitClient, 'post', fake_post, raising=False)
    monkeypatch.setattr(UpbitClient, 'MIN_KRW_BUY', 0)

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
    monkeypatch.setattr(UpbitClient, 'MIN_KRW_BUY', 0)

    client = UpbitClient('a', 'b')
    client.place_order('KRW-XRP', 'bid', 2.0, 50.0, 'price')

    assert captured['params']['ord_type'] == 'price'
    assert captured['params']['price'] == '100.0'
    assert 'volume' not in captured['params']


def test_minimum_buy_limit(monkeypatch):
    client = UpbitClient('a', 'b')
    client.MIN_KRW_BUY = 5000
    with pytest.raises(ValueError):
        client.place_order('KRW-XRP', 'bid', 1.0, 100.0, 'price')


def test_limit_price_rounded(monkeypatch):
    captured = {}

    def fake_post(self, path, params=None):
        captured['params'] = params
        return {'uuid': '1', 'state': 'done'}

    monkeypatch.setattr(UpbitClient, 'post', fake_post, raising=False)

    client = UpbitClient('a', 'b')
    client.place_order('KRW-ONDO', 'ask', 1.0, 1186.75, 'limit')

    assert captured['params']['price'] == '1185'


def test_cancel_order(monkeypatch):
    captured = {}

    def fake_delete(self, path, params=None):
        captured['path'] = path
        captured['params'] = params
        return {'uuid': params['uuid'], 'state': 'cancel'}

    monkeypatch.setattr(UpbitClient, 'delete', fake_delete, raising=False)
    client = UpbitClient('a', 'b')
    resp = client.cancel_order('123')
    assert captured['path'] == '/v1/order'
    assert captured['params']['uuid'] == '123'
    assert resp['state'] == 'cancel'
