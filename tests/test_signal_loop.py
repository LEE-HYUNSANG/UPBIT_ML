import os
import sys
import types
try:
    import pandas as pd
except Exception:
    pandas_available = False
else:
    pandas_available = True

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import importlib


import pytest


@pytest.mark.skipif(not pandas_available, reason="pandas not available")
def test_process_symbol_ignores_imported_strategy(monkeypatch):
    df = pd.DataFrame({
        "timestamp": [pd.Timestamp("2024-01-01")],
        "open": [1],
        "high": [1],
        "low": [1],
        "close": [1],
        "volume": [1],
    })
    stub = types.ModuleType("pyupbit")
    stub.get_ohlcv = lambda *a, **k: df
    monkeypatch.setitem(sys.modules, "pyupbit", stub)
    import signal_loop
    importlib.reload(signal_loop)

    captured = {}

    def dummy_f2(df1, df5, symbol="", calc_buy=True, calc_sell=True, strategy_codes=None, **kw):
        captured["codes"] = strategy_codes
        return {"symbol": symbol, "buy_signal": False, "sell_signal": False, "buy_triggers": [], "sell_triggers": []}

    monkeypatch.setattr(signal_loop, "f2_signal", dummy_f2)

    signal_loop._default_executor.position_manager.positions = [
        {"symbol": "KRW-BTC", "status": "open", "strategy": "imported"}
    ]

    signal_loop.process_symbol("KRW-BTC")
    assert captured["codes"] is None
