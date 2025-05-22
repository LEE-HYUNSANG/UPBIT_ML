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
