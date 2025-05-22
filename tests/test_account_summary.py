import pytest
from bot.trader import UpbitTrader

class DummyUpbit:
    def get_balances(self):
        return [{"currency": "AAA", "balance": "2"}, {"currency": "KRW", "balance": "1000"}]


def test_account_summary_skips_failed(monkeypatch):
    tr = UpbitTrader("k", "s", {})
    tr.upbit = DummyUpbit()
    tr._failed_until["AAA"] = 9999999999

    called = False

    def fake_price(*a, **k):
        nonlocal called
        called = True
        return 500.0

    monkeypatch.setattr("pyupbit.get_current_price", fake_price)
    summary = tr.account_summary()
    assert summary == {"cash": 1000, "total": 1000, "pnl": 0.0}
    assert called is False
