import pytest

from app import app, start_bot, trader, settings


def test_start_bot_uses_trader_config(monkeypatch):
    messages = []
    monkeypatch.setattr('app.notify', lambda m: messages.append(m))
    monkeypatch.setattr('app.get_filtered_tickers', lambda: ['KRW-TEST'])
    monkeypatch.setattr(trader, 'set_tickers', lambda tickers: None)
    monkeypatch.setattr(trader, 'start', lambda: True)

    monkeypatch.setitem(trader.config, 'amount', 11111)
    monkeypatch.setitem(trader.config, 'max_positions', 3)
    settings.running = False
    settings.buy_amount = 22222
    settings.max_positions = 9

    with app.test_request_context('/api/start-bot', method='POST'):
        resp = start_bot()
    assert resp.json['result'] == 'success'
    assert messages and '11,111' in messages[0] and '3종목' in messages[0]
