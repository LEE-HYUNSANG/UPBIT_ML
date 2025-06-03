import importlib.util
import json
from pathlib import Path

MODULE_PATH = Path(__file__).resolve().parents[1] / "f1_universe" / "01.coin_conditions.py"
spec = importlib.util.spec_from_file_location("coin_cond", MODULE_PATH)
coin_cond = importlib.util.module_from_spec(spec)
spec.loader.exec_module(coin_cond)


def test_select_coins_filters(tmp_path, monkeypatch):
    def dummy_fetch_markets():
        return ["KRW-AAA", "KRW-BBB", "BTC-ETH"]

    def dummy_fetch_candles(market):
        return [{}] * 6

    def dummy_fetch_ticker(market):
        if market == "KRW-AAA":
            return {"trade_price": 1500, "acc_trade_price_24h": 2_000_000_000}
        if market == "KRW-BBB":
            return {"trade_price": 5000, "acc_trade_price_24h": 2_000_000_000}
        return {}

    monkeypatch.setattr(coin_cond, "fetch_markets", dummy_fetch_markets)
    monkeypatch.setattr(coin_cond, "fetch_candles", dummy_fetch_candles)
    monkeypatch.setattr(coin_cond, "fetch_ticker", dummy_fetch_ticker)

    old_min, old_max = coin_cond.PRICE1_MIN, coin_cond.PRICE1_MAX
    coin_cond.PRICE1_MIN = 1000
    coin_cond.PRICE1_MAX = 3000

    coins = coin_cond.select_coins()
    assert coins == ["KRW-AAA"]

    out = tmp_path / "list.json"
    coin_cond.save_coin_list(coins, path=out)
    with open(out, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert data == ["KRW-AAA"]

    coin_cond.PRICE1_MIN, coin_cond.PRICE1_MAX = old_min, old_max


def test_price2_disabled(monkeypatch):
    old_p1_min, old_p1_max = coin_cond.PRICE1_MIN, coin_cond.PRICE1_MAX
    old_min, old_max = coin_cond.PRICE2_MIN, coin_cond.PRICE2_MAX
    coin_cond.PRICE1_MIN = 1000
    coin_cond.PRICE1_MAX = 3000
    coin_cond.PRICE2_MIN = 0
    coin_cond.PRICE2_MAX = 0

    monkeypatch.setattr(coin_cond, "fetch_markets", lambda: ["KRW-AAA"])
    monkeypatch.setattr(coin_cond, "fetch_candles", lambda market: [{}] * 6)
    monkeypatch.setattr(
        coin_cond,
        "fetch_ticker",
        lambda market: {"trade_price": 20000, "acc_trade_price_24h": 2_000_000_000},
    )

    coins = coin_cond.select_coins()
    assert coins == []

    coin_cond.PRICE1_MIN, coin_cond.PRICE1_MAX = old_p1_min, old_p1_max
    coin_cond.PRICE2_MIN, coin_cond.PRICE2_MAX = old_min, old_max
