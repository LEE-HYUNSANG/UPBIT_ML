import threading

import pytest



def dummy_risk_manager(*args, **kwargs):
    class RM:
        def update_account(self, *a, **k):
            pass
        def periodic(self):
            pass
    return RM()


def test_main_loop_invokes_hold_loop(monkeypatch):
    import importlib, sys, types

    pyupbit = types.ModuleType("pyupbit")
    pyupbit.get_ohlcv = lambda *a, **k: None
    sys.modules["pyupbit"] = pyupbit
    stub = types.ModuleType("signal_engine")
    stub.f2_signal = lambda *a, **k: {}
    stub.reload_strategy_settings = lambda: None
    sys.modules["f2_ml_buy_signal.03_buy_signal_engine.signal_engine"] = stub

    import signal_loop
    importlib.reload(signal_loop)

    calls = []
    monkeypatch.setattr(signal_loop._default_executor, "update_from_risk_config", lambda: None)
    monkeypatch.setattr(signal_loop._default_executor.position_manager, "sync_with_universe", lambda u: None)
    monkeypatch.setattr(signal_loop._default_executor.position_manager, "hold_loop", lambda: calls.append("h"))
    monkeypatch.setattr(signal_loop, "RiskManager", lambda *a, **k: dummy_risk_manager())
    monkeypatch.setattr(signal_loop, "init_coin_positions", lambda *a, **k: None)
    monkeypatch.setattr(signal_loop, "load_config", lambda: {})
    monkeypatch.setattr(signal_loop, "select_universe", lambda cfg: [])
    monkeypatch.setattr(signal_loop, "get_universe", lambda: [])
    monkeypatch.setattr(signal_loop, "schedule_universe_updates", lambda *a, **k: None)
    monkeypatch.setattr(signal_loop, "process_symbol", lambda *a, **k: None)
    stop_event = threading.Event()
    monkeypatch.setattr(signal_loop.time, "sleep", lambda x: stop_event.set())
    signal_loop.main_loop(interval=0, stop_event=stop_event)
    assert calls == ["h"]


def test_monitor_worker_invokes_hold_loop(monkeypatch):
    import importlib, sys, types

    pyupbit = types.ModuleType("pyupbit")
    pyupbit.get_ohlcv = lambda *a, **k: None
    sys.modules["pyupbit"] = pyupbit
    stub = types.ModuleType("signal_engine")
    stub.f2_signal = lambda *a, **k: {}
    stub.reload_strategy_settings = lambda: None
    sys.modules["f2_ml_buy_signal.03_buy_signal_engine.signal_engine"] = stub

    import signal_loop
    importlib.reload(signal_loop)

    import app
    app.stop_monitoring()
    calls = []
    monkeypatch.setattr(signal_loop._default_executor, "update_from_risk_config", lambda: None)
    monkeypatch.setattr(signal_loop._default_executor.position_manager, "hold_loop", lambda: calls.append("h"))
    monkeypatch.setattr(signal_loop, "RiskManager", lambda *a, **k: dummy_risk_manager())
    monkeypatch.setattr(signal_loop, "init_coin_positions", lambda *a, **k: None)

    class DummyThread:
        def __init__(self, target=None, daemon=None):
            self._target = target
        def start(self):
            self._target()
        def is_alive(self):
            return False
    monkeypatch.setattr(app.threading, "Thread", DummyThread)
    monkeypatch.setattr(app.time, "sleep", lambda x: app._monitor_stop.set())

    app.start_monitoring()
    assert calls == ["h"]
    app.stop_monitoring()
