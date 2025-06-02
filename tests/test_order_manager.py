import os
import sqlite3
import json
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from f3_order.position_manager import PositionManager
from f3_order.kpi_guard import KPIGuard
from f3_order.exception_handler import ExceptionHandler
from f3_order.upbit_api import UpbitClient


def make_pm(tmp_path, monkeypatch=None):
    cfg = {
        "DB_PATH": os.path.join(tmp_path, "orders.db"),
        "TP_PCT": 1.0,
        "SL_PCT": 1.0,
        "POSITIONS_FILE": os.path.join(tmp_path, "pos.json"),
        "PYR_ENABLED": False,
        "AVG_ENABLED": False,
    }
    guard = KPIGuard({})
    handler = ExceptionHandler({"SLIP_MAX": 0.15})
    if monkeypatch is not None:
        class DummyClient:
            def place_order(self, *args, **kwargs):
                return {
                    "uuid": "1",
                    "state": "done",
                    "side": kwargs.get("side"),
                    "volume": kwargs.get("volume"),
                }

            def get_accounts(self):
                return []

            def ticker(self, markets):
                return [{"market": m, "trade_price": 100.0} for m in markets]

        monkeypatch.setattr("f3_order.position_manager.UpbitClient", lambda: DummyClient())
    return PositionManager(cfg, guard, handler)


def test_execute_sell_closes_position(tmp_path, monkeypatch):
    pm = make_pm(tmp_path, monkeypatch)
    calls = []
    pm.exception_handler.send_alert = lambda m, s="info", *a: calls.append((m, s))
    order = {"symbol": "KRW-BTC", "price": 100.0, "qty": 1.0}
    pm.open_position(order)
    pm.positions[0]["current_price"] = 101.0
    pm.execute_sell(pm.positions[0], "take_profit")
    assert pm.positions[0]["status"] == "closed"
    conn = sqlite3.connect(os.path.join(tmp_path, "orders.db"))
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM orders")
    assert cur.fetchone()[0] == 2
    conn.close()
    assert calls and "KRW-BTC" in calls[0][0]


def test_execute_sell_sends_two_alerts(tmp_path, monkeypatch):
    pm = make_pm(tmp_path, monkeypatch)
    calls = []
    pm.exception_handler.send_alert = lambda m, s="info", *a: calls.append(m)
    order = {"symbol": "KRW-BTC", "price": 100.0, "qty": 1.0}
    pm.open_position(order)
    pm.positions[0]["current_price"] = 101.0
    pm.execute_sell(pm.positions[0], "take_profit")
    assert len(calls) == 2
    assert "매도 시도" in calls[0]
    assert "매도" in calls[1]


def test_execute_sell_wait_does_not_close(tmp_path, monkeypatch):
    class WaitClient:
        def place_order(self, *args, **kwargs):
            return {
                "uuid": "2",
                "state": "wait",
                "side": kwargs.get("side"),
                "volume": kwargs.get("volume"),
                "price": kwargs.get("price"),
            }

        def get_accounts(self):
            return []

        def ticker(self, markets):
            return [{"market": m, "trade_price": 100.0} for m in markets]

    monkeypatch.setattr("f3_order.position_manager.UpbitClient", lambda: WaitClient())
    pm = make_pm(tmp_path)
    calls = []
    pm.exception_handler.send_alert = lambda m, s="info", *a: calls.append(m)
    order = {"symbol": "KRW-BTC", "price": 100.0, "qty": 1.0}
    pm.open_position(order)
    pm.positions[0]["current_price"] = 101.0
    pm.execute_sell(pm.positions[0], "take_profit")
    assert pm.positions[0]["status"] == "open"
    assert len(calls) == 1
    assert "매도 시도" in calls[0]


def test_slippage_handling(tmp_path, monkeypatch):
    pm = make_pm(tmp_path, monkeypatch)
    order = {"symbol": "KRW-BTC", "price": 100.0, "qty": 1.0}
    pm.open_position(order)
    info = {"slippage_pct": 0.2}
    pm.exception_handler.handle_slippage("KRW-BTC", info)
    assert pm.exception_handler.slippage_count["KRW-BTC"] == 1


def test_update_position_from_fill(tmp_path, monkeypatch):
    pm = make_pm(tmp_path, monkeypatch)
    order = {"symbol": "KRW-BTC", "price": 100.0, "qty": 1.0}
    pm.open_position(order)
    fill = {
        "market": "KRW-BTC",
        "side": "ask",
        "volume": "1.0",
        "price": "101.0",
    }
    pm.update_position_from_fill("1", fill)
    assert pm.positions[0]["status"] == "closed"


def test_place_order_partial_fill(tmp_path, monkeypatch):
    class PartialFillClient:
        def place_order(self, *args, **kwargs):
            return {
                "uuid": "2",
                "state": "wait",
                "side": kwargs.get("side"),
                "market": kwargs.get("market"),
                "volume": kwargs.get("volume"),
                "remaining_volume": "1.0",
                "executed_volume": "1.0",
                "price": kwargs.get("price"),
            }

        def get_accounts(self):
            return []

        def ticker(self, markets):
            return [{"market": m, "trade_price": 100.0} for m in markets]

    monkeypatch.setattr("f3_order.position_manager.UpbitClient", lambda: PartialFillClient())
    pm = make_pm(tmp_path)
    pm.place_tp_order = lambda p: None
    order = {"symbol": "KRW-BTC", "price": 100.0, "qty": 2.0}
    pm.open_position(order)
    pm.place_order("KRW-BTC", "sell", 2.0, "market", 100.0)
    assert pm.positions[0]["qty"] == 1.0
    assert pm.positions[0]["status"] == "open"


def test_open_position_stores_strategy(tmp_path, monkeypatch):
    pm = make_pm(tmp_path, monkeypatch)
    pm.positions_file = os.path.join(tmp_path, "pos.json")
    order = {"symbol": "KRW-BTC", "price": 100.0, "qty": 1.0, "strategy": "TEST"}
    pm.open_position(order)
    with open(pm.positions_file, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert data and data[0]["strategy"] == "TEST"


def test_stop_loss_cancels_tp_order(tmp_path, monkeypatch):
    class DummyClient:
        def __init__(self):
            self.cancelled = []

        def place_order(self, *args, **kwargs):
            if kwargs.get("ord_type") == "limit":
                return {"uuid": "tp", "state": "wait", "side": "ask"}
            return {"uuid": "sl", "state": "done", "side": "ask"}

        def cancel_order(self, uuid):
            self.cancelled.append(uuid)

        def get_accounts(self):
            return []

        def ticker(self, markets):
            return []

    monkeypatch.setattr("f3_order.position_manager.UpbitClient", lambda: DummyClient())
    sell_cfg = tmp_path / "sell.json"
    with open(sell_cfg, "w", encoding="utf-8") as f:
        json.dump({"KRW-BTC": {"TP_PCT": 1.0, "SL_PCT": 1.0}}, f)
    pm = PositionManager(
        {
            "DB_PATH": os.path.join(tmp_path, "orders.db"),
            "POSITIONS_FILE": os.path.join(tmp_path, "pos.json"),
            "SELL_LIST_PATH": str(sell_cfg),
            "TP_PCT": 1.0,
            "SL_PCT": 1.0,
            "PYR_ENABLED": False,
            "AVG_ENABLED": False,
        },
        KPIGuard({}),
        ExceptionHandler({"SLIP_MAX": 0.15}),
    )
    pm.open_position({"symbol": "KRW-BTC", "price": 100.0, "qty": 1.0})
    pos = pm.positions[0]
    pos["current_price"] = 98.0
    pm.hold_loop()
    assert pm.client.cancelled == ["tp"]

def test_tp_cancels_when_price_above_entry(tmp_path, monkeypatch):
    class DummyClient:
        def __init__(self):
            self.cancelled = []
        def place_order(self, *args, **kwargs):
            if kwargs.get("ord_type") == "limit":
                return {"uuid": "tp", "state": "wait", "side": "ask"}
            return {"uuid": "m", "state": "done", "side": "ask"}
        def cancel_order(self, uuid):
            self.cancelled.append(uuid)
        def get_accounts(self):
            return []
        def ticker(self, markets):
            return []
    monkeypatch.setattr("f3_order.position_manager.UpbitClient", lambda: DummyClient())
    sell_cfg = tmp_path / "sell.json"
    with open(sell_cfg, "w", encoding="utf-8") as f:
        json.dump({"KRW-BTC": {"TP_PCT": 2.0, "SL_PCT": 1.0}}, f)
    pm = PositionManager(
        {
            "DB_PATH": os.path.join(tmp_path, "orders.db"),
            "POSITIONS_FILE": os.path.join(tmp_path, "pos.json"),
            "SELL_LIST_PATH": str(sell_cfg),
            "TP_PCT": 2.0,
            "SL_PCT": 1.0,
            "PYR_ENABLED": False,
            "AVG_ENABLED": False,
        },
        KPIGuard({}),
        ExceptionHandler({"SLIP_MAX": 0.15}),
    )
    pm.open_position({"symbol": "KRW-BTC", "price": 100.0, "qty": 1.0})
    pos = pm.positions[0]
    pos["avg_price"] = 100.0
    pos["current_price"] = 101.0
    pm.hold_loop()
    assert pm.client.cancelled == []

def test_tp_kept_when_price_below_entry(tmp_path, monkeypatch):
    class DummyClient:
        def __init__(self):
            self.cancelled = []
        def place_order(self, *args, **kwargs):
            if kwargs.get("ord_type") == "limit":
                return {"uuid": "tp", "state": "wait", "side": "ask"}
            return {"uuid": "m", "state": "done", "side": "ask"}
        def cancel_order(self, uuid):
            self.cancelled.append(uuid)
        def get_accounts(self):
            return []
        def ticker(self, markets):
            return []
    monkeypatch.setattr("f3_order.position_manager.UpbitClient", lambda: DummyClient())
    sell_cfg = tmp_path / "sell.json"
    with open(sell_cfg, "w", encoding="utf-8") as f:
        json.dump({"KRW-BTC": {"TP_PCT": 2.0, "SL_PCT": 1.0}}, f)
    pm = PositionManager(
        {
            "DB_PATH": os.path.join(tmp_path, "orders.db"),
            "POSITIONS_FILE": os.path.join(tmp_path, "pos.json"),
            "SELL_LIST_PATH": str(sell_cfg),
            "TP_PCT": 2.0,
            "SL_PCT": 1.0,
            "PYR_ENABLED": False,
            "AVG_ENABLED": False,
        },
        KPIGuard({}),
        ExceptionHandler({"SLIP_MAX": 0.15}),
    )
    pm.open_position({"symbol": "KRW-BTC", "price": 100.0, "qty": 1.0})
    pos = pm.positions[0]
    pos["avg_price"] = 100.0
    pos["current_price"] = 99.5
    pm.hold_loop()
    assert pm.client.cancelled == ["tp"]
