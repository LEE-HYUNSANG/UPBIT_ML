import logging
from logging.handlers import RotatingFileHandler

if __name__ == "__main__" and __package__ is None:
    import sys
    from pathlib import Path

    sys.path.append(str(Path(__file__).resolve().parents[1]))

from .smart_buy import smart_buy
from .position_manager import PositionManager
from .kpi_guard import KPIGuard
from .exception_handler import ExceptionHandler
from f6_setting.alarm_control import get_template
from .utils import load_config, log_with_tag
from f6_setting.buy_config import load_buy_config
import time
import json
from pathlib import Path

logger = logging.getLogger("F3_order_executor")
fh = RotatingFileHandler(
    "logs/F3_order_executor.log",
    encoding="utf-8",
    maxBytes=100_000 * 1024,
    backupCount=1000,
)
formatter = logging.Formatter('%(asctime)s [F3] %(message)s')
fh.setFormatter(formatter)
logger.addHandler(fh)
logger.setLevel(logging.INFO)


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

    def _update_realtime_sell_list(self, symbol: str) -> None:
        """Add TP/SL info for *symbol* to the realtime sell list."""
        sell_path = Path("config") / "f3_f3_realtime_sell_list.json"
        mon_path = Path("config") / "f5_f1_monitoring_list.json"

        try:
            with open(sell_path, "r", encoding="utf-8") as f:
                sell_data = json.load(f)
            if not isinstance(sell_data, dict):
                sell_data = {}
        except Exception:
            sell_data = {}

        if symbol in sell_data:
            return

        try:
            with open(mon_path, "r", encoding="utf-8") as f:
                mon_list = json.load(f)
        except Exception:
            return

        thresh = None
        loss = None
        if isinstance(mon_list, list):
            for item in mon_list:
                if isinstance(item, dict) and item.get("symbol") == symbol:
                    thresh = item.get("thresh_pct")
                    loss = item.get("loss_pct")
                    break
        if thresh is None or loss is None:
            return

        sell_data[symbol] = {
            "TP_PCT": float(thresh) * 100,
            "SL_PCT": float(loss) * 100,
        }

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
                if self.risk_manager and self.risk_manager.is_symbol_disabled(symbol):
                    log_with_tag(logger, f"Entry blocked by RiskManager for {symbol}")
                    return
                if (
                    hasattr(self.position_manager, "positions")
                    and any(
                        p.get("symbol") == symbol
                        and p.get("status") in ("open", "pending")
                        for p in self.position_manager.positions
                    )
                ):
                    log_with_tag(logger, f"Buy skipped: already holding {symbol}")
                    return
                max_retry = int(self.config.get("MAX_RETRY", 3))
                order_result = {}
                for attempt in range(max_retry):
                    order_result = smart_buy(
                        signal,
                        self.config,
                        self.position_manager,
                        logger,
                    )
                    if order_result.get("filled"):
                        break
                    if attempt < max_retry - 1:
                        time.sleep(3)
                if order_result.get("filled", False):
                    if signal.get("buy_triggers"):
                        order_result["strategy"] = signal["buy_triggers"][0]
                    self.position_manager.open_position(order_result)
                    self._update_realtime_sell_list(symbol)
                    self._mark_buy_filled(symbol)
                    log_with_tag(logger, f"Buy executed: {order_result}")
                    template = get_template("buy")
                    msg = template.format(
                        symbol=order_result["symbol"],
                        price=order_result.get("price"),
                    )
                    self.exception_handler.send_alert(msg, "info", "order_execution")
                else:
                    if signal.get("buy_triggers"):
                        order_result["strategy"] = signal["buy_triggers"][0]
                    self.position_manager.open_position(order_result, status="pending")
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
