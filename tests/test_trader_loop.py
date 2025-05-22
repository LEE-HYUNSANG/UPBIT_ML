import pandas as pd
import pytest
from bot.trader import UpbitTrader

class DummyUpbit:
    def __init__(self):
        self.last = None
    def get_balances(self):
        return []
    def buy_market_order(self, ticker, amount):
        self.last = amount
        return {"price": 1000.0, "volume": amount / 1000.0}
    def sell_market_order(self, ticker, qty):
        return {}

def test_buy_market_order_uses_krw(monkeypatch):
    up = DummyUpbit()
    conf = {"amount": 10000, "tickers": ["KRW-TEST"]}
    tr = UpbitTrader("k", "s", conf)
    tr.upbit = up

    df = pd.DataFrame({"open": [1]*120, "high": [1]*120, "low": [1]*120,
                        "close": [1000]*120, "volume": [1]*120})
    monkeypatch.setattr("pyupbit.get_ohlcv", lambda *a, **k: df)
    monkeypatch.setattr("bot.trader.calc_indicators", lambda d: d)
    monkeypatch.setattr("bot.trader.calc_tis", lambda t: 100.0)
    monkeypatch.setattr("bot.trader.df_to_market", lambda d, t: {})
    monkeypatch.setattr("bot.trader.check_buy_signal", lambda s, l, m: True)
    monkeypatch.setattr("bot.trader.check_sell_signal", lambda s, l, m: False)
    monkeypatch.setattr("time.sleep", lambda x: (_ for _ in ()).throw(SystemExit))

    tr.running = True
    with pytest.raises(SystemExit):
        tr.run_loop()
    assert up.last == 10000
