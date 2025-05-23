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


def test_save_load_cycle(tmp_path):
    path = tmp_path / "active.json"
    from helpers.utils import positions as pos
    data = {"KRW-BTC": {"qty": 0.1, "buy_price": 10, "strategy": "S", "level": "공격적"}}
    pos.save_open_positions(data, str(path))
    loaded = pos.load_open_positions(str(path))
    assert loaded == data


def test_sync_positions_restores_strategy(monkeypatch, tmp_path):
    path = tmp_path / "active.json"
    from helpers.utils import positions as pos
    monkeypatch.setattr(pos, "POS_FILE", str(path))
    pos.save_open_positions({"KRW-BTC": {"strategy": "EMA", "level": "공격적"}}, str(path))

    class U:
        def get_balances(self):
            return [{"currency": "BTC", "balance": "0.1", "avg_buy_price": "1000"}]

    tr = UpbitTrader("k", "s", {"level": "중도적"})
    tr.upbit = U()
    tr.sync_positions()
    assert tr.positions["KRW-BTC"]["strategy"] == "EMA"
    assert tr.positions["KRW-BTC"]["level"] == "공격적"


def test_refresh_positions_uses_saved(monkeypatch, tmp_path):
    path = tmp_path / "active.json"
    from helpers.utils import positions as pos
    monkeypatch.setattr(pos, "POS_FILE", str(path))
    pos.save_open_positions({"KRW-BTC": {"strategy": "EMA", "level": "공격적"}}, str(path))

    class Up:
        def __init__(self):
            self.called = 0

        def get_balances(self):
            self.called += 1
            return [{"currency": "BTC", "balance": "1", "avg_buy_price": "100"}]

    up = Up()
    act = {}
    from helpers import bot
    monkeypatch.setattr(bot, "_safe_call", lambda f, *a, **k: f(*a, **k))
    bot.refresh_positions(up, act)
    assert act["KRW-BTC"]["strategy"] == "EMA"
    assert act["KRW-BTC"]["level"] == "공격적"
