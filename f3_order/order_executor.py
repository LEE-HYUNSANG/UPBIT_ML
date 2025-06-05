import sys
from pathlib import Path
import os

import logging
from logging.handlers import RotatingFileHandler
from common_utils import DedupFilter

from .smart_buy import smart_buy
import threading
from .position_manager import PositionManager
from common_utils import load_json
from .kpi_guard import KPIGuard
from .exception_handler import ExceptionHandler
from .utils import load_config, log_with_tag, pretty_symbol
import time
from f6_setting.buy_config import load_buy_config
from f6_setting.sell_config import load_sell_config
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
logger.propagate = False
logger.addFilter(DedupFilter(60))
if os.environ.get("PYTEST_CURRENT_TEST"):
    logger.disabled = True

_startup_time = time.time()

# Use an absolute path to the project root to avoid issues when this module is
# executed from a different working directory.
ROOT_DIR = Path(__file__).resolve().parents[1]


def _resolve_path(path: str | Path) -> Path:
    """Return *path* as a Path, searching the project root if necessary."""
    p = Path(path)
    if p.is_absolute() or p.exists():
        return p
    return ROOT_DIR / p


@contextmanager
def _buy_list_lock(path: str | Path, retries: int = 50, delay: float = 0.1):
    """Yield an exclusive file handle for the realtime buy list.

    Parameters
    ----------
    path : str or Path
        File to lock for exclusive access.
    retries : int, optional
        Number of attempts to open and lock the file.
    delay : float, optional
        Sleep time between retries in seconds.

    Yields
    ------
    file
        Open file handle positioned at the start of the file.
    """
    if os.environ.get("UPBIT_DISABLE_LOCKS"):
        fh = Path(path).open("a+")
        fh.seek(0)
        try:
            yield fh
        finally:
            fh.close()
        return

    lock_file = Path(path)
    fh = None
    for _ in range(retries):
        try:
            fh = lock_file.open("a+")
            fh.seek(0)
            break
        except PermissionError as exc:
            log_with_tag(logger, f"PermissionError opening {lock_file}: {exc}")
            time.sleep(delay)
    if fh is None:
        raise PermissionError(f"Cannot open {lock_file}")

    locked = False
    for _ in range(retries):
        try:
            if fcntl:
                fcntl.flock(fh, fcntl.LOCK_EX)
            else:  # pragma: no cover - Windows
                msvcrt.locking(fh.fileno(), msvcrt.LK_LOCK, 1)
            locked = True
            break
        except PermissionError:
            time.sleep(delay)
    if not locked:
        fh.close()
        raise PermissionError(f"Cannot lock {lock_file}")

    fh.seek(0)
    try:
        yield fh
    finally:
        try:
            fh.seek(0)
            if fcntl:
                fcntl.flock(fh, fcntl.LOCK_UN)
            else:  # pragma: no cover - Windows
                try:
                    msvcrt.locking(fh.fileno(), msvcrt.LK_UNLCK, 1)
                except PermissionError as exc:
                    log_with_tag(logger, f"unlock error {lock_file}: {exc}")
        finally:
            fh.close()


class OrderExecutor:
    def __init__(
        self,
        config_path=None,
        buy_path="config/f6_buy_settings.json",
        sell_path="config/f6_sell_settings.json",
        risk_manager=None,
    ):
        self.config_path = config_path
        self.buy_path = buy_path
        self.sell_path = sell_path
        self.config: dict = {}
        if config_path:
            p = _resolve_path(config_path)
            if p.exists():
                self.config.update(load_config(str(p)))
        self.config.update(load_buy_config(str(_resolve_path(buy_path))))
        self.config.update(load_sell_config(str(_resolve_path(sell_path))))
        ts_flag = str(self.config.get("TS_FLAG", "OFF")).upper()
        self.config["TRAILING_STOP_ENABLED"] = ts_flag == "ON"
        self.kpi_guard = KPIGuard(self.config)
        self.exception_handler = ExceptionHandler(self.config)
        self.risk_manager = risk_manager
        self.position_manager = PositionManager(
            self.config, self.kpi_guard, self.exception_handler, logger
        )
        self._pending_cache: tuple[float, set[str]] | None = None
        self.pending_symbols: set[str] = self._load_pending_flags()
        self._pending_lock = threading.Lock()
        if self.risk_manager:
            self.update_from_risk_config()
        log_with_tag(logger, "OrderExecutor initialized.")

    def _count_active_positions(self, threshold: float = 5000.0) -> int:
        """Return the number of open or pending positions with value >= *threshold*."""
        positions = getattr(self.position_manager, "positions", None)
        if not isinstance(positions, list):
            return 0
        count = 0
        for pos in positions:
            if pos.get("status") in ("open", "pending"):
                try:
                    price = float(pos.get("entry_price", 0))
                    qty = float(pos.get("qty", 0))
                    if price * qty >= threshold:
                        count += 1
                except Exception:
                    continue
        return count

    def set_risk_manager(self, rm):
        self.risk_manager = rm
        self.update_from_risk_config()

    def reload_config(self) -> None:
        """Reload buy/sell settings from their JSON files."""
        try:
            self.config.update(load_buy_config(str(_resolve_path(self.buy_path))))
            self.config.update(load_sell_config(str(_resolve_path(self.sell_path))))
            log_with_tag(logger, f"Config reloaded: ENTRY_SIZE_INITIAL={self.config.get('ENTRY_SIZE_INITIAL')}")
        except Exception as exc:  # pragma: no cover - best effort
            log_with_tag(logger, f"Config reload failed: {exc}")

    def update_from_risk_config(self):
        """Mirror relevant values from the associated RiskManager."""
        if not self.risk_manager:
            return
        entry_size = self.risk_manager.config.get("ENTRY_SIZE_INITIAL")
        if entry_size is not None:
            self.config["ENTRY_SIZE_INITIAL"] = entry_size

    def _mark_buy_filled(self, symbol: str) -> None:
        """Set ``buy_count`` to 1 for the given symbol in the buy list."""
        path = _resolve_path("config/f2_f2_realtime_buy_list.json")
        if not path.exists():
            return
        with _buy_list_lock(path) as fh:
            try:
                data = json.load(fh)
                if not isinstance(data, list) or not data:
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
                    fh.seek(0)
                    fh.truncate()
                    json.dump(data, fh, ensure_ascii=False, indent=2)
                except Exception:
                    pass

    def _set_pending_flag(self, symbol: str, value: int) -> None:
        """Update ``pending`` field for *symbol* in the buy list."""
        path = _resolve_path("config/f2_f2_realtime_buy_list.json")
        if not path.exists():
            return
        with _buy_list_lock(path) as fh:
            try:
                data = json.load(fh)
                if not isinstance(data, list) or not data:
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
                    fh.seek(0)
                    fh.truncate()
                    json.dump(data, fh, ensure_ascii=False, indent=2)
                except Exception:
                    pass

    def _load_pending_flags(self) -> set[str]:
        """Return symbols with ``pending`` flag set in the buy list."""
        now_ts = time.time()
        if self._pending_cache and now_ts - self._pending_cache[0] < 1:
            return set(self._pending_cache[1])

        path = _resolve_path("config/f2_f2_realtime_buy_list.json")
        for _ in range(5):
            try:
                with _buy_list_lock(path) as fh:
                    data = json.load(fh)
                    if isinstance(data, list):
                        result = {
                            item.get("symbol")
                            for item in data
                            if isinstance(item, dict) and item.get("pending")
                        }
                        self._pending_cache = (now_ts, result)
                        return result
            except PermissionError as exc:
                log_with_tag(logger, f"Pending flag read error: {exc}")
                time.sleep(0.1)
            except Exception:
                break
        self._pending_cache = (now_ts, set())
        return set()


    def _update_realtime_sell_list(self, symbol: str) -> None:
        """Add *symbol* to the realtime sell list if missing."""
        sell_path = _resolve_path("config/f3_f3_realtime_sell_list.json")
        if not sell_path.exists():
            return

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

    def entry(self, signal) -> bool:
        """Process a buy signal and attempt to open a position.

        Parameters
        ----------
        signal : dict
            Output from the F2 module containing at least ``symbol`` and
            ``buy_signal`` keys.

        Returns
        -------
        bool
            ``True`` if an order was executed or recorded as pending.
        """
        try:
            log_with_tag(logger, f"Entry signal received: {signal}")
            self.reload_config()
            delay = int(self.config.get("STARTUP_HOLD_SEC", 0))
            if delay > 0 and not os.environ.get("PYTEST_CURRENT_TEST"):
                elapsed = time.time() - _startup_time
                if elapsed < delay:
                    remain = int(delay - elapsed)
                    log_with_tag(logger, f"Buy skipped: startup delay {remain}s remaining")
                    return False
            if signal["buy_signal"]:
                symbol = signal.get("symbol")
                price = signal.get("price")
                with self._pending_lock:
                    self.pending_symbols.update(self._load_pending_flags())
                    if symbol in self.pending_symbols:
                        log_with_tag(logger, f"Buy skipped: order already pending for {symbol}")
                        return False
                if self.config.get("MAX_SYMBOLS") is not None and \
                        self._count_active_positions() >= int(self.config["MAX_SYMBOLS"]):
                    log_with_tag(logger, "Buy skipped: MAX_SYMBOLS limit reached")
                    return False
                with self._pending_lock:
                    self.pending_symbols.add(symbol)
                self._set_pending_flag(symbol, 1)
                self._mark_buy_filled(symbol)
                if self.risk_manager and self.risk_manager.is_symbol_disabled(symbol):
                    log_with_tag(logger, f"Entry blocked by RiskManager for {symbol}")
                    return False
                has_pos = getattr(self.position_manager, "has_position", None)
                if callable(has_pos) and has_pos(symbol):
                    log_with_tag(logger, f"Buy skipped: already holding {symbol}")
                    return False
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
                if signal.get("price") is not None:
                    order_result["entry_price"] = signal["price"]
                if order_result.get("filled", False):
                    if signal.get("buy_triggers"):
                        order_result["strategy"] = signal["buy_triggers"][0]
                    self._update_realtime_sell_list(symbol)
                    self.position_manager.open_position(order_result)
                    self._set_pending_flag(symbol, 0)
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
                        self._set_pending_flag(symbol, 0)
                        return False
                    elif (
                        not callable(getattr(self.position_manager, "has_position", None))
                        or not self.position_manager.has_position(symbol)
                    ):
                        if signal.get("buy_triggers"):
                            order_result["strategy"] = signal["buy_triggers"][0]
                        self.position_manager.open_position(order_result, status="pending")
                        self._mark_buy_filled(symbol)
                        log_with_tag(logger, f"Pending buy recorded: {order_result}")
                        return True
                    return False
            else:
                log_with_tag(logger, f"No buy signal for {signal.get('symbol')}")
                return False
        except Exception as e:
            self.exception_handler.handle(e, context="entry")
            self._set_pending_flag(signal.get("symbol"), 0)
            return False
        return True

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

def entry(signal) -> bool:
    """Convenience wrapper that forwards ``signal`` to the default executor.

    Parameters
    ----------
    signal : dict
        F2 signal dictionary passed directly to :meth:`OrderExecutor.entry`.

    Returns
    -------
    bool
        Result from :meth:`OrderExecutor.entry`.
    """
    return _default_executor.entry(signal)


if __name__ == "__main__":  # pragma: no cover - manual execution
    print("OrderExecutor ready. Use order_executor.entry(signal) to submit orders.")
