import types
from helpers import bot

class DummyUpbit:
    def __init__(self):
        self.called = 0
    def get_balances(self):
        self.called += 1
        return [{"currency": "BTC", "balance": "0.5", "avg_buy_price": "100"}]


def test_refresh_positions(monkeypatch):
    up = DummyUpbit()
    act = {"KRW-ETH": {"qty": 1, "buy_price": 200, "strategy": "S", "level": "중"}}
    monkeypatch.setattr(bot, "_safe_call", lambda f, *a, **k: f(*a, **k))
    bot.refresh_positions(up, act)
    assert "KRW-BTC" in act and "KRW-ETH" not in act
    assert up.called == 1
