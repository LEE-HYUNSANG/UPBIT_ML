import importlib
import os
import sys
import types
import json
import pytest
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


@pytest.fixture
def app_client(monkeypatch):
    # Stub check_signals to avoid file access
    stub = types.ModuleType("f2_buy_signal")
    stub.check_signals = lambda symbol: {"signal1": True, "signal2": True, "signal3": True}
    stub.reload_strategy_settings = lambda: None
    monkeypatch.setitem(sys.modules, "f2_buy_signal.03_buy_signal_engine.signal_engine", stub)
    monkeypatch.setitem(sys.modules, "f2_ml_buy_signal.03_buy_signal_engine.signal_engine", stub)

    # Provide a dummy pyupbit module
    dummy_pyupbit = types.ModuleType("pyupbit")
    dummy_pyupbit.get_ohlcv = lambda *args, **kwargs: None
    monkeypatch.setitem(sys.modules, "pyupbit", dummy_pyupbit)
    # Stub requests module used by universe selector
    if "requests" not in sys.modules:
        monkeypatch.setitem(sys.modules, "requests", types.SimpleNamespace())

    # Stub jwt used by fetch_account_info
    jwt_stub = types.ModuleType("jwt")
    jwt_stub.encode = lambda payload, secret: "token"
    monkeypatch.setitem(sys.modules, "jwt", jwt_stub)

    # Minimal Flask substitute with test client support
    flask_stub = types.ModuleType("flask")
    import json as _json

    class Response:
        def __init__(self, data, status=200):
            if isinstance(data, str):
                self.data = data
            else:
                self.data = _json.dumps(data)
            self.status_code = status

        def get_json(self):
            try:
                return _json.loads(self.data)
            except Exception:
                return None

    class Flask:
        def __init__(self, name):
            self.routes = {}

        def route(self, rule, methods=["GET"]):
            methods_key = tuple(sorted(m.upper() for m in methods))

            def decorator(func):
                self.routes[(rule, methods_key)] = func
                return func

            return decorator

        def test_client(self):
            app = self

            class Client:
                def get(self, path):
                    func = app.routes.get((path, ("GET",))) or app.routes.get((path, ("GET", "POST")))
                    return func()

            return Client()

    def jsonify(obj):
        return Response(obj)

    flask_stub.Flask = Flask
    flask_stub.jsonify = jsonify
    flask_stub.Response = Response
    flask_stub.render_template = lambda *a, **k: ""
    flask_stub.request = types.SimpleNamespace(args={}, method="GET", get_json=lambda force=False: {})
    monkeypatch.setitem(sys.modules, "flask", flask_stub)

    class DummyClient:
        def place_order(self, market, side, volume, price=None, ord_type="market"):
            return {
                "uuid": "1",
                "state": "done",
                "side": side,
                "volume": str(volume),
                "price": price,
            }

        def get_accounts(self):
            return []

        def ticker(self, markets):
            return [{"market": m, "trade_price": 100.0} for m in markets]

    monkeypatch.setattr("f3_order.position_manager.UpbitClient", lambda: DummyClient())

    # Simplify smart_buy to include qty/price for position opening
    monkeypatch.setattr(
        "f3_order.smart_buy.smart_buy",
        lambda signal, config, pm=None, parent_logger=None: {
            "filled": True,
            "symbol": signal["symbol"],
            "order_type": "market",
            "qty": 1.0,
            "price": 100.0,
        },
    )

    import f3_order.order_executor as order_executor
    importlib.reload(order_executor)
    import signal_loop
    importlib.reload(signal_loop)

    class DummyDF:
        def reset_index(self):
            return self
        def rename(self, *args, **kwargs):
            return self
        @property
        def empty(self):
            return False
    monkeypatch.setattr(signal_loop.pyupbit, "get_ohlcv", lambda symbol, interval, count=50: DummyDF())

    # Prevent network operations in universe selector during app import
    monkeypatch.setattr("f1_universe.universe_selector.load_config", lambda: {})
    monkeypatch.setattr("f1_universe.universe_selector.load_universe_from_file", lambda: None)
    monkeypatch.setattr("f1_universe.universe_selector.schedule_universe_updates", lambda *a, **k: None)
    monkeypatch.setattr("f1_universe.universe_selector.select_universe", lambda cfg: ["KRW-BTC"])
    monkeypatch.setattr("f1_universe.universe_selector.get_universe", lambda: ["KRW-BTC"])
    monkeypatch.setattr("f1_universe.universe_selector.update_universe", lambda cfg: None)

    rm = None

    import app
    importlib.reload(app)
    app.app.testing = True
    return app.app.test_client(), order_executor, rm


def test_api_account(app_client, monkeypatch):
    client, _, _ = app_client
    monkeypatch.setattr("app.fetch_account_info", lambda: {"krw_balance": 500, "pnl": 1.5})
    res = client.get("/api/account")
    assert res.status_code == 200
    assert res.get_json() == {"krw_balance": 500, "pnl": 1.5}



def test_universe_config_endpoint(app_client, monkeypatch):
    client, _, _ = app_client
    cfg = {"min_price": 1, "max_price": 2, "min_volatility": 0.1, "volume_rank": 10}
    monkeypatch.setattr("f1_universe.universe_selector.load_config", lambda: cfg)
    import app as app_mod
    monkeypatch.setattr(app_mod, "load_config", lambda: cfg)
    resp = client.get("/api/universe_config")
    data = resp.get_json()
    assert resp.status_code == 200
    assert data["min_price"] == 1
    assert data["volume_rank"] == 10


def test_auto_trade_status_and_positions(app_client, tmp_path, monkeypatch):
    client, order_executor, _ = app_client
    import app as app_mod

    status_file = tmp_path / "status.json"
    monkeypatch.setattr(app_mod, "AUTOTRADE_STATUS_FILE", str(status_file))

    resp = client.get("/api/auto_trade_status")
    data = resp.get_json()
    assert resp.status_code == 200
    assert data["enabled"] is False

    order_executor._default_executor.position_manager.positions = [
        {"symbol": "KRW-BTC", "status": "open", "qty": 1}
    ]
    pos_resp = client.get("/api/open_positions")
    assert pos_resp.get_json()[0]["symbol"] == "KRW-BTC"


def test_open_positions_empty(app_client):
    client, order_executor, _ = app_client
    # Ensure no positions are registered
    order_executor._default_executor.position_manager.positions = []
    resp = client.get("/api/open_positions")
    assert resp.status_code == 200
    assert resp.get_json() == []


def test_pending_positions_not_listed(app_client):
    client, order_executor, _ = app_client
    order_executor._default_executor.position_manager.positions = [
        {"symbol": "KRW-NEO", "status": "pending", "qty": 1.0}
    ]
    resp = client.get("/api/open_positions")
    assert resp.status_code == 200
    assert resp.get_json() == []
    order_executor._default_executor.position_manager.positions = []


def test_events_endpoint(app_client, tmp_path, monkeypatch):
    client, _, _ = app_client
    import app as app_mod

    log = tmp_path / "events.jsonl"
    monkeypatch.setattr(app_mod, "EVENTS_LOG", str(log))
    log.write_text('{"timestamp": "10:00", "message": "test"}\n')
    resp = client.get("/api/events")
    assert resp.get_json()[0]["message"] == "test"


def test_strategies_endpoint(app_client, tmp_path, monkeypatch):
    client, _, _ = app_client
    import app as app_mod

    cfg = tmp_path / "strategies.json"
    cfg.write_text('[{"short_code":"AAA","on":true,"order":1}]')
    master = tmp_path / "master.json"
    master.write_text('[{"short_code":"AAA","buy_formula":"f"}]')
    monkeypatch.setattr(app_mod, "STRATEGY_SETTINGS_FILE", str(cfg))
    monkeypatch.setattr(app_mod, "STRATEGY_YDAY_FILE", str(tmp_path / "yday.json"))
    monkeypatch.setattr(app_mod, "STRATEGIES_MASTER_FILE", str(master))

    resp = client.get("/api/strategies")
    data = resp.get_json()
    assert resp.status_code == 200
    assert data["strategies"][0]["name"] == "AAA"


def test_strategies_post_reload(app_client, tmp_path, monkeypatch):
    client, _, _ = app_client
    import app as app_mod

    cfg = tmp_path / "strategies.json"
    master = tmp_path / "master.json"
    master.write_text('[{"short_code":"AAA","buy_formula":"f"}]')
    monkeypatch.setattr(app_mod, "STRATEGY_SETTINGS_FILE", str(cfg))
    monkeypatch.setattr(app_mod, "STRATEGY_YDAY_FILE", str(tmp_path / "yday.json"))
    monkeypatch.setattr(app_mod, "STRATEGIES_MASTER_FILE", str(master))

    called = {}

    def fake_reload():
        called["reloaded"] = True

    monkeypatch.setattr(app_mod, "reload_strategy_settings", fake_reload)

    from flask import request as flask_request
    flask_request.method = "POST"
    flask_request.get_json = lambda force=False: [{"short_code": "AAA", "on": False, "order": 1}]

    resp = client.get("/api/strategies")
    data = resp.get_json()
    assert resp.status_code == 200
    assert data["status"] == "ok"
    assert called.get("reloaded") is True


def test_buy_monitoring_endpoint(app_client, tmp_path, monkeypatch):
    client, _, _ = app_client
    import app as app_mod

    buy_file = tmp_path / "f2_f3_realtime_buy_list.json"
    buy_file.write_text(
        '[{"symbol":"KRW-AAA","buy_signal":1,"trend_sel":1,"rsi_sel":1}]'
    )
    metrics_file = tmp_path / "selected_strategies.json"
    metrics_file.write_text(
        '[{"symbol":"KRW-AAA","win_rate":0.8,"avg_roi":0.01}]'
    )

    real_join = app_mod.os.path.join

    def fake_join(*parts):
        if parts == (
            "config",
            "f2_f3_realtime_buy_list.json",
        ):
            return str(buy_file)
        if parts == (
            "f5_ml_pipeline",
            "ml_data",
            "10_selected",
            "selected_strategies.json",
        ):
            return str(metrics_file)
        return real_join(*parts)

    monkeypatch.setattr(app_mod.os.path, "join", fake_join)
    monkeypatch.setattr(app_mod.os.path, "getmtime", lambda p: 0)

    res = client.get("/api/buy_monitoring")
    data = res.get_json()
    assert res.status_code == 200
    assert data[0]["symbol"] == "KRW-AAA"
    assert data[0]["win_rate"] == 0.8


def test_buy_settings_endpoint(app_client, tmp_path, monkeypatch):
    client, _, _ = app_client
    import app as app_mod

    cfg = tmp_path / "buy.json"
    monkeypatch.setattr(app_mod, "BUY_SETTINGS_FILE", str(cfg))

    resp = client.get("/api/buy_settings")
    data = resp.get_json()
    assert data["ENTRY_SIZE_INITIAL"] == 7000

    monkeypatch.setattr(app_mod.request, "method", "POST")
    monkeypatch.setattr(app_mod.request, "get_json", lambda force=False: {"ENTRY_SIZE_INITIAL": 20000})
    resp = client.get("/api/buy_settings")
    assert resp.status_code == 200
    assert json.loads(cfg.read_text())["ENTRY_SIZE_INITIAL"] == 20000


def test_alarm_config_endpoint(app_client, tmp_path, monkeypatch):
    client, _, _ = app_client
    import app as app_mod

    cfg = tmp_path / "alarm.json"
    monkeypatch.setattr(app_mod, "ALARM_CONFIG_FILE", str(cfg))

    resp = client.get("/api/alarm_config")
    data = resp.get_json()
    assert data["system_start_stop"] is True

    monkeypatch.setattr(app_mod.request, "method", "POST")
    monkeypatch.setattr(app_mod.request, "get_json", lambda force=False: {"system_start_stop": False})
    resp = client.get("/api/alarm_config")
    assert resp.status_code == 200
    assert json.loads(cfg.read_text())["system_start_stop"] is False

