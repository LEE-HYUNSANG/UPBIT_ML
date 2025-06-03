import sys
from pathlib import Path
import os

import logging
from logging.handlers import RotatingFileHandler

from .smart_buy import smart_buy
import threading
from .position_manager import PositionManager
from common_utils import load_json
from .kpi_guard import KPIGuard
from .exception_handler import ExceptionHandler
from .utils import load_config, log_with_tag, pretty_symbol
from f6_setting.buy_config import load_buy_config
import json
from contextlib import contextmanager

try:
    import fcntl
except Exception:  # pragma: no cover - Windows
    fcntl = None  # type: ignore
    import msvcrt

logger = logging.getLogger("F3_order_executor")
os.makedirs("logs/f3", exist_ok=True)
fh = RotatingFileHandler(
    "logs/f3/F3_order_executor.log",
    encoding="utf-8",
    maxBytes=100_000 * 1024,
    backupCount=1000,
)
formatter = logging.Formatter('%(asctime)s [F3] %(message)s')
fh.setFormatter(formatter)
logger.addHandler(fh)
logger.setLevel(logging.INFO)


@contextmanager
def _buy_list_lock(path: str | Path):
    """Context manager providing an exclusive lock on *path*."""
    lock_file = Path(path)
    fh = lock_file.open("a+")
    try:
        if fcntl:
            fcntl.flock(fh, fcntl.LOCK_EX)
        else:  # pragma: no cover - Windows
            msvcrt.locking(fh.fileno(), msvcrt.LK_LOCK, 1)
        yield
    finally:
        try:
            if fcntl:
                fcntl.flock(fh, fcntl.LOCK_UN)
            else:  # pragma: no cover - Windows
                msvcrt.locking(fh.fileno(), msvcrt.LK_UNLCK, 1)
        finally:
            fh.close()


class OrderExecutor:
    def __init__(self, config_path="config/f3_f3_order_config.json", buy_path="config/f6_buy_settings.json", risk_manager=None):
        self.config = load_config(config_path)
        self.config.update(load_buy_config(buy_path))
        self.kpi_guard = KPIGuard(self.config)
        self.exception_handler = ExceptionHandler(self.config)
        self.risk_manager = risk_manager
        self.position_manager = PositionManager(
            self.config, self.kpi_guard, self.exception_handler, logger
        )
        self.pending_symbols: set[str] = self._load_pending_flags()
        self._pending_lock = threading.Lock()
        if self.risk_manager:
            self.update_from_risk_config()
        log_with_tag(logger, "OrderExecutor initialized.")

    def set_risk_manager(self, rm):
        self.risk_manager = rm
        self.update_from_risk_config()

    def update_from_risk_config(self):
        """Mirror relevant values from the associated RiskManager."""
        if not self.risk_manager:
            return
        entry_size = self.risk_manager.config.get("ENTRY_SIZE_INITIAL")
        if entry_size is not None:
            self.config["ENTRY_SIZE_INITIAL"] = entry_size

    def _mark_buy_filled(self, symbol: str) -> None:
        """Set ``buy_count`` to 1 for the given symbol in the buy list."""
        path = Path("config") / "f2_f2_realtime_buy_list.json"
        with _buy_list_lock(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if not isinstance(data, list):
                    return
            except Exception:
                return

            changed = False
            for item in data:
                if item.get("symbol") == symbol:
                    if item.get("buy_count", 0) != 1:
                        item["buy_count"] = 1
                        changed = True
                    break
            if changed:
                try:
                    with open(path, "w", encoding="utf-8") as f:
                        json.dump(data, f, ensure_ascii=False, indent=2)
                except Exception:
                    pass

    def _set_pending_flag(self, symbol: str, value: int) -> None:
        """Update ``pending`` field for *symbol* in the buy list."""
        path = Path("config") / "f2_f2_realtime_buy_list.json"
        with _buy_list_lock(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if not isinstance(data, list):
                    return
            except Exception:
                return

            changed = False
            for item in data:
                if item.get("symbol") == symbol:
                    if item.get("pending", 0) != value:
                        item["pending"] = value
                        changed = True
                    break
            if changed:
                try:
                    with open(path, "w", encoding="utf-8") as f:
                        json.dump(data, f, ensure_ascii=False, indent=2)
                except Exception:
                    pass

    def _load_pending_flags(self) -> set[str]:
        """Return symbols with ``pending`` flag set in the buy list."""
        path = Path("config") / "f2_f2_realtime_buy_list.json"
        with _buy_list_lock(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if isinstance(data, list):
                    return {
                        item.get("symbol")
                        for item in data
                        if isinstance(item, dict) and item.get("pending")
                    }
            except Exception:
                pass
        return set()


    def _update_realtime_sell_list(self, symbol: str) -> None:
        """Add *symbol* to the realtime sell list if missing."""
        sell_path = Path("config") / "f3_f3_realtime_sell_list.json"

        try:
            with open(sell_path, "r", encoding="utf-8") as f:
                sell_data = json.load(f)
            if not isinstance(sell_data, list):
                sell_data = []
        except Exception:
            sell_data = []

        if symbol in sell_data:
            return

        sell_data.append(symbol)
        try:
            with open(sell_path, "w", encoding="utf-8") as f:
                json.dump(sell_data, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def entry(self, signal):
        """F2 신호 딕셔너리 → smart_buy 주문 (filled시 포지션 오픈)"""
        try:
            log_with_tag(logger, f"Entry signal received: {signal}")
            if signal["buy_signal"]:
                symbol = signal.get("symbol")
                price = signal.get("price")
                with self._pending_lock:
                    self.pending_symbols.update(self._load_pending_flags())
                    if symbol in self.pending_symbols:
                        log_with_tag(logger, f"Buy skipped: order already pending for {symbol}")
                        return
                    self.pending_symbols.add(symbol)
                self._set_pending_flag(symbol, 1)
                if self.risk_manager and self.risk_manager.is_symbol_disabled(symbol):
                    log_with_tag(logger, f"Entry blocked by RiskManager for {symbol}")
                    return
                has_pos = getattr(self.position_manager, "has_position", None)
                if callable(has_pos) and has_pos(symbol):
                    log_with_tag(logger, f"Buy skipped: already holding {symbol}")
                    return
                self.exception_handler.send_alert(
                    f"매수 시그널] {pretty_symbol(symbol)} @{price}",
                    "info",
                    "buy_monitoring",
                )
                order_result = {}
                try:
                    order_result = smart_buy(
                        signal,
                        self.config,
                        self.position_manager,
                        logger,
                    )
                finally:
                    with self._pending_lock:
                        self.pending_symbols.discard(symbol)
                    self._set_pending_flag(symbol, 0)
                if signal.get("price") is not None:
                    order_result["entry_price"] = signal["price"]
                if order_result.get("filled", False):
                    if signal.get("buy_triggers"):
                        order_result["strategy"] = signal["buy_triggers"][0]
                    self._update_realtime_sell_list(symbol)
                    self.position_manager.open_position(order_result)
                    self._mark_buy_filled(symbol)
                    log_with_tag(logger, f"Buy executed: {order_result}")
                    price_exec = order_result.get("price") or 0
                    qty_exec = order_result.get("qty") or 0
                    fee = float(order_result.get("paid_fee", 0))
                    total = price_exec * qty_exec + fee
                    msg = (
                        f"매수 주문 성공] {pretty_symbol(order_result['symbol'])} "
                        f"매수 금액: {int(total):,}원 @{price_exec}"
                    )
                    self.exception_handler.send_alert(msg, "info", "order_execution")
                else:
                    if order_result.get("canceled"):
                        log_with_tag(logger, f"Buy canceled for {symbol}")
                    elif not callable(getattr(self.position_manager, "has_position", None)) or not self.position_manager.has_position(symbol):
                        if signal.get("buy_triggers"):
                            order_result["strategy"] = signal["buy_triggers"][0]
                        self.position_manager.open_position(order_result, status="pending")
                        self._mark_buy_filled(symbol)
                        log_with_tag(logger, f"Pending buy recorded: {order_result}")
            else:
                log_with_tag(logger, f"No buy signal for {signal.get('symbol')}")
        except Exception as e:
            self.exception_handler.handle(e, context="entry")

    def manage_positions(self):
        """1Hz 루프: 포지션 관리 FSM (불타기, 물타기, 익절, 손절 등)"""
        self.position_manager.refresh_positions()
        self.position_manager.hold_loop()

    def check_quality(self):
        """KPI Guard 품질 체크 (승률, 손익 등)"""
        self.kpi_guard.check(logger)

    def handle_exceptions(self):
        """장애/슬리피지/오더 오류 등 감지 및 처리"""
        self.exception_handler.periodic_check(logger)


_default_executor = OrderExecutor()

def entry(signal):
    """기본 실행기를 사용하는 하위 호환 엔트리 포인트"""
    _default_executor.entry(signal)


if __name__ == "__main__":  # pragma: no cover - manual execution
    print("OrderExecutor ready. Use order_executor.entry(signal) to submit orders.")
