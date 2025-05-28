import pytest

try:
    import pandas as pd
except Exception:
    pandas_available = False
else:
    pandas_available = True

import importlib
import sys
import types

pyupbit = types.ModuleType("pyupbit")
pyupbit.get_ohlcv = lambda *a, **k: None
sys.modules["pyupbit"] = pyupbit

requests = types.ModuleType("requests")
requests.get = lambda *a, **k: None
sys.modules["requests"] = requests

signal_engine_stub = types.ModuleType("signal_engine")
signal_engine_stub.f2_signal = lambda *a, **k: {}
signal_engine_stub.reload_strategy_settings = lambda: None
sys.modules["f2_signal.signal_engine"] = signal_engine_stub

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

    def fake_f2(df1, df5, symbol, calc_buy=True, calc_sell=True, strategy_codes=None):
        captured['codes'] = strategy_codes
        return {"symbol": symbol, "buy_signal": False, "sell_signal": False, "buy_triggers": [], "sell_triggers": []}

    monkeypatch.setattr(signal_loop, "f2_signal", fake_f2)
    monkeypatch.setattr(signal_loop, "f3_entry", lambda *a, **k: None)
    signal_loop._default_executor.position_manager.positions = [
        {"symbol": "KRW-AAA", "status": "open", "strategy": "imported"}
    ]
    signal_loop.process_symbol("KRW-AAA")
    assert captured.get('codes') is None
