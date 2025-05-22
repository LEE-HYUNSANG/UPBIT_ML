import pytest
from bot.trader import UpbitTrader

class DummyUpbit:
    def get_balances(self):
        return [{"currency": "AAA", "balance": "2"}, {"currency": "KRW", "balance": "1000"}]


def test_account_summary_records_failure(monkeypatch):
    tr = UpbitTrader("k", "s", {})
    tr.upbit = DummyUpbit()

    def fake_price(*a, **k):
        raise Exception("fail")

    monkeypatch.setattr("pyupbit.get_current_price", fake_price)
    summary = tr.account_summary()
    assert summary == {"cash": 1000, "total": 1000, "pnl": 0.0}
    assert tr._fail_counts.get("AAA") == 1
