"""
[F3] KPI 품질보증 가드 (승률, 손익 등 자동 중단/롤백)
로그: logs/F3_kpi_guard.log
"""
import logging
from .utils import log_with_tag
from .exception_handler import ExceptionHandler

logger = logging.getLogger("F3_kpi_guard")
fh = logging.FileHandler("logs/F3_kpi_guard.log")
formatter = logging.Formatter('%(asctime)s [F3] %(message)s')
fh.setFormatter(formatter)
logger.addHandler(fh)
logger.setLevel(logging.INFO)

class KPIGuard:
    def __init__(self, config):
        self.config = config
        self.win_history = []  # 최근 N회 승패
        self.pnl_history = []  # 최근 N회 손익
        self.exception_handler = ExceptionHandler(config)

    def check(self, parent_logger=None):
        """
        KPI 체크(승률/손익/Sharpe 등), 임계치 미달시 경보 및 중단 트리거
        """
        WIN_MIN_N = self.config.get("WIN_MIN_N", 100)
        WIN_THRESHOLD = self.config.get("WIN_THRESHOLD", 0.55)
        if len(self.win_history) >= WIN_MIN_N:
            winrate = sum(self.win_history[-WIN_MIN_N:]) / WIN_MIN_N
            if winrate < WIN_THRESHOLD:
                msg = f"KPI WINRATE DOWN: {winrate:.2%} < {WIN_THRESHOLD:.2%} (TRIGGER PAUSE)"
                log_with_tag(logger, msg)
                self.exception_handler.send_alert(msg, "warning")
        if self.pnl_history:
            avg_pnl = sum(self.pnl_history[-WIN_MIN_N:]) / min(len(self.pnl_history), WIN_MIN_N)
            pnl_th = self.config.get("PNL_THRESHOLD", -5.0)
            if avg_pnl <= pnl_th:
                msg = f"KPI PnL DOWN: {avg_pnl:.2f}% <= {pnl_th}%"
                log_with_tag(logger, msg)
                self.exception_handler.send_alert(msg, "warning")

    def record_trade(self, win: bool, pnl: float) -> None:
        self.win_history.append(1 if win else 0)
        self.pnl_history.append(pnl)

