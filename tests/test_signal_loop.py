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
    called = {}
    monkeypatch.setattr(signal_loop, "check_signals", lambda sym: called.setdefault("sym", sym) or {"signal1": True, "signal2": True, "signal3": True})
    pm = signal_loop._default_executor.position_manager
    pm.positions = [{"symbol": "KRW-BTC", "status": "open", "strategy": "imported"}]
    signal_loop.process_symbol("KRW-BTC")
    assert called["sym"] == "KRW-BTC"

