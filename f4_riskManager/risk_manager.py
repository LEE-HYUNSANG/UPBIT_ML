"""
F4 RiskManager - 실시간 리스크 감시, 상태머신, 자동 조치
로그: logs/F4_risk_manager.log
"""
from .risk_config import RiskConfig
from .risk_logger import RiskLogger
from .risk_utils import RiskState, now
import json
import os
import datetime


def _now_kst():
    tz = datetime.timezone(datetime.timedelta(hours=9))
    return datetime.datetime.now(tz).isoformat(timespec="seconds")


def _log_jsonl(path: str, data: dict) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)
        f.write("\n")


def _log_fsm(from_state: RiskState, to_state: RiskState, reason: str) -> None:
    data = {
        "time": _now_kst(),
        "event": "FSM Transition",
        "from": from_state.name,
        "to": to_state.name,
        "reason": reason,
    }
    _log_jsonl("logs/risk_fsm.log", data)
class RiskManager:
    def __init__(self, config_path="config/setting_date/f4_f3_latest_config.json", order_executor=None, exception_handler=None):
        self.config = RiskConfig(config_path)
        self.logger = RiskLogger("logs/F4_risk_manager.log")
        self.order_executor = order_executor
        self.exception_handler = exception_handler
        self.state = RiskState.ACTIVE
        self.daily_loss = 0.0
        self.mdd = 0.0
        self.monthly_mdd = 0.0
        self.slippage_events = {}
        self.open_symbols = set()
        self.disabled_symbols = set()
        self.pause_timer = None
        self._last_reload_check = 0

        self.logger.info("RiskManager 초기화 완료 (ACTIVE)")

    def set_order_executor(self, executor):
        self.order_executor = executor

    def set_exception_handler(self, handler):
        self.exception_handler = handler

    def close_all_positions(self):
        if self.order_executor:
            pm = getattr(self.order_executor, "position_manager", None)
            if pm:
                pm.close_all_positions()

    def update_account(self, account_pnl, mdd, monthly_mdd, open_symbols):
        """
        계좌/포지션 정보 최신화
        account_pnl: 일 실현 손익 (%)
        mdd: 30d MDD (%)
        monthly_mdd: 월 MDD (%)
        open_symbols: 현재 진입중 코인 set
        """
        self.daily_loss = account_pnl
        self.mdd = mdd
        self.monthly_mdd = monthly_mdd
        self.open_symbols = set(open_symbols)

    def on_slippage(self, symbol):
        """슬리피지 초과 이벤트 처리"""
        self.slippage_events[symbol] = self.slippage_events.get(symbol, 0) + 1
        self.logger.warn(f"{symbol} 슬리피지 초과: 누적 {self.slippage_events[symbol]}")
        if self.exception_handler:
            self.exception_handler.send_alert(
                f"{symbol} slippage event #{self.slippage_events[symbol]}", "warning", "system_alert"
            )
        max_slip = self.config.get("SLIP_FAIL_MAX", 5)
        if self.slippage_events[symbol] >= max_slip:
            self.disable_symbol(symbol)

    def check_risk(self):
        """
        1Hz 주기 실시간 리스크 체크 및 상태 전이
        """
        c = self.config
        # 일 최대 손실 감시
        if self.daily_loss <= -abs(c.get("DAILY_LOSS_LIM", 2.5)):
            self.pause(minutes=1440, reason="일손실 초과")
        # 30일 MDD 감시
        if self.mdd <= -abs(c.get("MDD_LIM", 7.0)):
            self.halt(reason="30일 MDD 초과")
        # 월 MDD 감시
        if self.monthly_mdd <= -abs(c.get("MONTHLY_MDD_LIM", 10.0)):
            self.halt(reason="월간 MDD 초과")
        # 동시 매매 코인 수 감시
        if len(self.open_symbols) > c.get("MAX_SYMBOLS", 5):
            self.logger.warn(f"동시매매 한도 초과! ({len(self.open_symbols)} > {c.get('MAX_SYMBOLS', 5)})")
            # 진입 차단 (진입 함수 내에서 활용)
        if hasattr(self, "order_fail_count") and self.order_fail_count > c.get("ORDER_FAIL_LIMIT", 5):
            self.pause(30, reason="주문 실패 누적")
        if hasattr(self, "ws_fail_count") and self.ws_fail_count > c.get("WS_FAIL_LIMIT", 3):
            self.pause(10, reason="WS 장애 누적")

    def pause(self, minutes, reason=""):
        """일시중단 상태 진입"""
        if self.state == RiskState.PAUSE:
            return
        prev = self.state
        self.close_all_positions()
        self.state = RiskState.PAUSE
        self.pause_timer = now() + minutes * 60  # 타임스탬프 기준
        self.logger.warn(f"상태전이: PAUSE - {reason}, {minutes}분간 신규진입 중단")
        _log_fsm(prev, self.state, reason)
        if self.exception_handler:
            self.exception_handler.send_alert(
                f"PAUSE: {reason}", "warning", "system_alert"
            )

    def disable_symbol(self, symbol):
        """특정 심볼(코인) 엔트리 중단"""
        self.logger.warn(f"{symbol} 진입중단(DISABLE) - 슬리피지 초과")
        if self.order_executor:
            pm = getattr(self.order_executor, "position_manager", None)
            if pm:
                for pos in list(pm.positions):
                    if pos.get("symbol") == symbol and pos.get("status") == "open":
                        pm.execute_sell(pos, "risk_disable", pos.get("qty"))
        if self.exception_handler:
            self.exception_handler.send_alert(
                f"DISABLE {symbol}", "warning", "system_alert"
            )
        self.disabled_symbols.add(symbol)

    def is_symbol_disabled(self, symbol: str) -> bool:
        """Return True if *symbol* is currently disabled."""
        return symbol in self.disabled_symbols

    def halt(self, reason=""):
        """전체 중단(HALT), 모든 포지션 청산"""
        if self.state == RiskState.HALT:
            return
        prev = self.state
        self.close_all_positions()
        self.state = RiskState.HALT
        self.logger.critical(f"상태전이: HALT - {reason}, 모든 포지션 청산 및 서비스 중단")
        _log_fsm(prev, self.state, reason)
        if self.exception_handler:
            self.exception_handler.send_alert(
                f"HALT: {reason}", "critical", "system_start_stop"
            )
        # 엔진에 전체 청산 명령 및 신규 진입 불가 트리거

    def hot_reload(self):
        """Reload risk config when ``config/setting_date/f4_f3_latest_config.json`` changes.

        ``periodic()`` checks for updates every second. When a modification is detected
        the new parameters are applied immediately, the ``OrderExecutor`` refreshes
        trade sizing and a notification is sent.
        """
        if self.config.reload():
            self.logger.info("리스크 파라미터 핫리로드 적용")
            if self.order_executor:
                self.order_executor.update_from_risk_config()
            if self.exception_handler:
                self.exception_handler.send_alert(
                    "Risk parameters reloaded", "info", "system_alert"
                )

    def periodic(self):
        """메인 루프(1Hz)에서 주기적 호출"""
        if self.state == RiskState.PAUSE and self.pause_timer and now() > self.pause_timer:
            self.state = RiskState.ACTIVE
            self.logger.info("PAUSE 해제 → ACTIVE 복귀")
            if self.exception_handler:
                self.exception_handler.send_alert(
                    "Trading resumed", "info", "system_start_stop"
                )
        current = now()
        if current - self._last_reload_check >= 1:
            self.hot_reload()
            self._last_reload_check = current
        self.check_risk()

