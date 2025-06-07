import pytest

try:
    import pandas as pd
except Exception:
    pandas_available = False
else:
    pandas_available = True
    import signal_loop


@pytest.mark.skipif(not pandas_available, reason="pandas not available")
def test_process_symbol_ignores_imported_strategy(monkeypatch):
    df = pd.DataFrame({
        "timestamp": pd.date_range("2021-01-01", periods=2, freq="T"),
        "open": [1, 2],
        "high": [1, 2],
        "low": [1, 2],
        "close": [1, 2],
        "volume": [1, 1],
    })
    monkeypatch.setattr(signal_loop, "fetch_ohlcv", lambda *a, **k: df)
    captured = {}

    def fake_f2(df1, df5, symbol="", calc_buy=True, calc_sell=True, strategy_codes=None):
        captured["codes"] = strategy_codes
        return {"symbol": symbol, "buy_signal": False, "sell_signal": False, "buy_triggers": [], "sell_triggers": []}

    monkeypatch.setattr(signal_loop, "f2_signal", fake_f2)
    pm = signal_loop._default_executor.position_manager
    pm.positions = [{"symbol": "KRW-BTC", "status": "open", "strategy": "imported"}]
    signal_loop.process_symbol("KRW-BTC")
    assert captured["codes"] is None


@pytest.mark.skipif(not pandas_available, reason="pandas not available")
def test_process_symbol_forwards_to_f3(monkeypatch):
    df = pd.DataFrame({
        "timestamp": pd.date_range("2021-01-01", periods=2, freq="T"),
        "open": [1, 2],
        "high": [1, 2],
        "low": [1, 2],
        "close": [1, 2],
        "volume": [1, 1],
    })

    monkeypatch.setattr(signal_loop, "fetch_ohlcv", lambda *a, **k: df)

    result_signal = {
        "symbol": "KRW-AAA",
        "buy_signal": True,
        "sell_signal": False,
        "buy_triggers": ["A"],
        "sell_triggers": [],
    }
    monkeypatch.setattr(signal_loop, "f2_signal", lambda *a, **k: result_signal)
    forwarded = {}
    monkeypatch.setattr(signal_loop, "f3_entry", lambda sig: forwarded.setdefault("sig", sig))
    signal_loop._default_executor.position_manager.positions = []

    res = signal_loop.process_symbol("KRW-AAA")
    assert forwarded.get("sig", {}).get("symbol") == "KRW-AAA"
    assert res.get("price") == 2.0


@pytest.mark.skipif(not pandas_available, reason="pandas not available")
def test_process_symbol_executes_sell(monkeypatch):
    df = pd.DataFrame({
        "timestamp": pd.date_range("2021-01-01", periods=2, freq="T"),
        "open": [1, 2],
        "high": [1, 2],
        "low": [1, 2],
        "close": [1, 2],
        "volume": [1, 1],
    })
    monkeypatch.setattr(signal_loop, "fetch_ohlcv", lambda *a, **k: df)

    monkeypatch.setattr(
        signal_loop,
        "f2_signal",
        lambda *a, **k: {
            "symbol": "KRW-BBB",
            "buy_signal": False,
            "sell_signal": True,
            "buy_triggers": [],
            "sell_triggers": ["A"],
        },
    )
    calls = {"sell": 0}
    pm = signal_loop._default_executor.position_manager
    pm.positions = [{"symbol": "KRW-BBB", "status": "open", "strategy": "A"}]
    monkeypatch.setattr(pm, "execute_sell", lambda *a, **k: calls.__setitem__("sell", calls["sell"] + 1))

    signal_loop.process_symbol("KRW-BBB")
    assert calls["sell"] == 1

