import os
import sys
import time
import tracemalloc
import logging

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from f3_order.order_executor import OrderExecutor
from f4_riskManager.risk_manager import RiskManager, RiskState


class DummyPositionManager:
    def __init__(self, *_, **__):
        self.positions = []

    def open_position(self, order_result):
        self.positions.append(order_result)

    def close_all_positions(self):
        for p in self.positions:
            p["status"] = "closed"

    def hold_loop(self):
        pass

    def execute_sell(self, pos, reason, qty=None):
        pos["status"] = "closed"


class DummyRiskLogger:
    def __init__(self, *_, **__):
        pass

    def info(self, msg):
        pass

    def warn(self, msg):
        pass

    def critical(self, msg):
        pass


class DummyRiskConfig:
    def __init__(self, *_):
        self._vals = {
            "DAILY_LOSS_LIM": 1.0,
            "MDD_LIM": 7.0,
            "MONTHLY_MDD_LIM": 10.0,
            "MAX_SYMBOLS": 5,
        }

    def reload(self):
        return False

    def get(self, key, default=None):
        return self._vals.get(key, default)


@pytest.fixture
def system(monkeypatch):
    monkeypatch.setattr("f3_order.order_executor.PositionManager", DummyPositionManager)
    monkeypatch.setattr("f3_order.order_executor.load_config", lambda p: {})
    monkeypatch.setattr(
        "f3_order.order_executor.smart_buy",
        lambda signal, config, dyn, logger=None: {
            "filled": True,
            "symbol": signal["symbol"],
            "qty": 1,
            "price": 1,
        },
    )
    monkeypatch.setattr("f4_riskManager.risk_manager.RiskLogger", DummyRiskLogger)
    monkeypatch.setattr("f4_riskManager.risk_manager.RiskConfig", DummyRiskConfig)

    dummy_logger = logging.getLogger("dummy")
    dummy_logger.addHandler(logging.NullHandler())
    monkeypatch.setattr("f3_order.order_executor.logger", dummy_logger)
    monkeypatch.setattr("f3_order.smart_buy.logger", dummy_logger)

    oe = OrderExecutor(risk_manager=None)
    rm = RiskManager(order_executor=None, exception_handler=oe.exception_handler)
    oe.set_risk_manager(rm)
    rm.set_order_executor(oe)
    return oe, rm


def test_stress_entry_and_risk(system):
    oe, rm = system
    rm.pause(0)  # start in PAUSE then immediately recover

    tracemalloc.start()
    start = time.perf_counter()
    for i in range(500):
        signal = {"symbol": f"KRW-{i}", "buy_signal": True, "spread": 0.0001}
        oe.entry(signal)
        rm.periodic()
    duration = time.perf_counter() - start
    current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    assert rm.state == RiskState.ACTIVE
    assert len(oe.position_manager.positions) == 500
    assert duration < 5.0
    assert peak < 50 * 1024 * 1024
