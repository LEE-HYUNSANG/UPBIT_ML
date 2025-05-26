import importlib
import os
import sys
import types
import pytest
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


@pytest.fixture
def app_client(monkeypatch):
    # Stub f2_signal module to avoid pandas dependency
    stub = types.ModuleType("signal_engine")
    def fake_f2_signal(df1, df5, symbol=""):
        return {
            "symbol": symbol,
            "buy_signal": True,
            "sell_signal": False,
            "buy_triggers": ["TEST"],
            "sell_triggers": [],
        }
    stub.f2_signal = fake_f2_signal
    monkeypatch.setitem(sys.modules, "f2_signal.signal_engine", stub)

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

    monkeypatch.setattr("f3_order.position_manager.UpbitClient", lambda: DummyClient())

    # Simplify smart_buy to include qty/price for position opening
    monkeypatch.setattr("f3_order.smart_buy.smart_buy", lambda signal, config, dynamic_params, parent_logger=None: {"filled": True, "symbol": signal["symbol"], "order_type": "market", "qty": 1.0, "price": 100.0})

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

    from f4_riskManager import RiskManager
    rm = RiskManager(order_executor=order_executor._default_executor,
                     exception_handler=order_executor._default_executor.exception_handler)
    order_executor._default_executor.set_risk_manager(rm)

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


def test_signals_and_risk(app_client, monkeypatch):
    client, order_executor, rm = app_client
    monkeypatch.setattr("f1_universe.universe_selector.get_universe", lambda: ["KRW-BTC"])
    res = client.get("/api/signals")
    data = res.get_json()
    assert res.status_code == 200
    assert data["KRW-BTC"]["buy_signal"] is True
    assert len(order_executor._default_executor.position_manager.positions) == 1
    rm.update_account(-3.0, 0.0, 0.0, ["KRW-BTC"])
    rm.periodic()
    assert rm.state.name == "PAUSE"
    events = client.get("/api/risk_events").get_json()
    assert any("PAUSE" in e["message"] for e in events)


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
