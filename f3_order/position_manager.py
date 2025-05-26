"""
[F3] 포지션 상태 관리(HOLD FSM, 불타기/물타기/익절/손절/트레일 등)
로그: logs/F3_position_manager.log
"""
import logging
from .utils import log_with_tag, now

logger = logging.getLogger("F3_position_manager")
fh = logging.FileHandler("logs/F3_position_manager.log")
formatter = logging.Formatter('%(asctime)s [F3] %(message)s')
fh.setFormatter(formatter)
logger.addHandler(fh)
logger.setLevel(logging.INFO)

class PositionManager:
    def __init__(self, config, dynamic_params, kpi_guard, exception_handler, parent_logger=None):
        self.config = config
        self.dynamic_params = dynamic_params
        self.kpi_guard = kpi_guard
        self.exception_handler = exception_handler
        self.positions = []

    def open_position(self, order_result):
        """ 신규 포지션 오픈 (filled 주문 결과 기반) """
        pos = {
            "symbol": order_result["symbol"],
            "entry_time": now(),
            "entry_price": order_result.get("price", None),
            "qty": order_result.get("qty", None),
            "pyramid_count": 0,
            "avgdown_count": 0,
            "status": "open",
        }
        self.positions.append(pos)
        log_with_tag(logger, f"Open position: {pos}")

    def hold_loop(self):
        """
        1Hz 루프: 각 포지션별 FSM 관리 (불타기/물타기/익절/손절/트레일/타임스탑 등)
        ※ 조건/산식은 config와 dynamic_params 기준. (실제 시세 연동 필요)
        """
        for pos in self.positions:
            # TODO: 실시간 시세/ATR/RSI 등 조건 반영
            log_with_tag(logger, f"Position checked: {pos['symbol']} status: {pos['status']}")
            # 예시: 만료/익절/손절시 포지션 종료
            # if 조건: pos['status'] = 'closed'
        # 포지션 종료/정리 처리도 필요 (리스트에서 제거 등)
