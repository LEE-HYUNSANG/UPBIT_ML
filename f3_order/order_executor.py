import logging
from .smart_buy import smart_buy
from .position_manager import PositionManager
from .kpi_guard import KPIGuard
from .exception_handler import ExceptionHandler
from .utils import load_config, now, log_with_tag

logger = logging.getLogger("F3_order_executor")
fh = logging.FileHandler("logs/F3_order_executor.log")
formatter = logging.Formatter('%(asctime)s [F3] %(message)s')
fh.setFormatter(formatter)
logger.addHandler(fh)
logger.setLevel(logging.INFO)


class OrderExecutor:
    def __init__(self, config_path="config/order.json", dyn_param_path="config/dynamic_params.json"):
        self.config = load_config(config_path)
        self.dynamic_params = load_config(dyn_param_path)
        self.kpi_guard = KPIGuard(self.config)
        self.exception_handler = ExceptionHandler(self.config)
        self.position_manager = PositionManager(
            self.config, self.dynamic_params, self.kpi_guard, self.exception_handler, logger
        )
        log_with_tag(logger, "OrderExecutor initialized.")

    def entry(self, signal):
        """F2 신호 딕셔너리 → smart_buy 주문 (filled시 포지션 오픈)"""
        try:
            if signal["buy_signal"]:
                order_result = smart_buy(signal, self.config, self.dynamic_params, logger)
                if order_result.get("filled", False):
                    self.position_manager.open_position(order_result)
                    log_with_tag(logger, f"Buy executed: {order_result}")
        except Exception as e:
            self.exception_handler.handle(e, context="entry")

    def manage_positions(self):
        """1Hz 루프: 포지션 관리 FSM (불타기, 물타기, 익절, 손절 등)"""
        self.position_manager.hold_loop()

    def check_quality(self):
        """KPI Guard 품질 체크 (승률, 손익 등)"""
        self.kpi_guard.check(logger)

    def handle_exceptions(self):
        """장애/슬리피지/오더 오류 등 감지 및 처리"""
        self.exception_handler.periodic_check(logger)


_default_executor = OrderExecutor()

def entry(signal):
    """Backward compatible entry point using a default executor."""
    _default_executor.entry(signal)
