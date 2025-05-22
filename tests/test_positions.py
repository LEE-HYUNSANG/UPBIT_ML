import pytest
from bot.trader import UpbitTrader

class DummyUpbit:
    def get_balances(self):
        return []


def test_build_positions_uses_saved_strategy(monkeypatch):
    conf = {"strategy": "M-BREAK", "level": "중도적", "params": {"sl": 0, "tp": 0}}
    tr = UpbitTrader("k", "s", conf)
    tr.upbit = DummyUpbit()
    monkeypatch.setattr("pyupbit.get_current_price", lambda *a, **k: 1000.0)
    balances = [{"currency": "BTC", "balance": "0.1", "avg_buy_price": "1000"}]
    tr.positions["KRW-BTC"] = {"strategy": "EMA-STACK", "level": "공격적"}
    result = tr.build_positions(balances)
    assert result and result[0]["strategy"] == "EMA-STACK"
    assert result[0]["level"] == "공격적"


def test_build_positions_records_failure(monkeypatch):
    conf = {}
    tr = UpbitTrader("k", "s", conf)
    tr.upbit = DummyUpbit()

    def fake_price(*a, **k):
        raise Exception("fail")

    monkeypatch.setattr("pyupbit.get_current_price", fake_price)
    balances = [{"currency": "AAA", "balance": "1", "avg_buy_price": "0"}]
    positions = tr.build_positions(balances)
    assert positions and positions[0]["coin"] == "AAA"
    assert tr._fail_counts.get("AAA") == 1
