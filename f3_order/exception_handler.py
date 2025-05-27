"""
[F3] 장애/슬리피지/오류 처리, 자동 롤백/경보
로그: logs/F3_exception_handler.log
"""
import logging
from logging.handlers import RotatingFileHandler
try:
    import requests
except Exception:  # pragma: no cover - offline test env
    requests = None
    import urllib.request as _urlreq
from urllib.parse import urlencode
from .utils import log_with_tag, load_env

logger = logging.getLogger("F3_exception_handler")
fh = RotatingFileHandler(
    "logs/F3_exception_handler.log",
    encoding="utf-8",
    maxBytes=100_000 * 1024,
    backupCount=1000,
)
formatter = logging.Formatter('%(asctime)s [F3] %(message)s')
fh.setFormatter(formatter)
logger.addHandler(fh)
logger.setLevel(logging.INFO)

class ExceptionHandler:
    def __init__(self, config):
        self.config = config
        self.slippage_count = {}
        env = load_env()
        self.tg_token = env.get("TELEGRAM_TOKEN")
        self.tg_chat_id = env.get("TELEGRAM_CHAT_ID")

    def send_alert(self, message: str, severity: str = "info") -> None:
        """Send a Telegram notification if credentials are set."""
        if not self.tg_token or not self.tg_chat_id:
            return
        text = f"[{severity.upper()}] {message}"
        url = f"https://api.telegram.org/bot{self.tg_token}/sendMessage"
        data = {"chat_id": self.tg_chat_id, "text": text}
        try:
            if requests:
                requests.post(url, data=data, timeout=5)
            else:
                req = _urlreq.Request(url, data=urlencode(data).encode())
                _urlreq.urlopen(req, timeout=5)
        except Exception:
            pass

    def handle(self, exception, context=""):
        """ 예외 상황 처리 및 로그 """
        log_with_tag(logger, f"Exception in {context}: {exception}")
        if isinstance(exception, RuntimeError):
            log_with_tag(logger, "Critical runtime error detected. Pausing trading.")
        elif isinstance(exception, ConnectionError):
            log_with_tag(logger, "Network error detected. Will retry automatically.")

    def periodic_check(self, parent_logger=None):
        """
        1Hz: 장애/슬리피지 등 실시간 감시/자동 조치
        """
        for symbol, cnt in list(self.slippage_count.items()):
            limit = self.config.get("SLIP_FAIL_MAX", 5)
            if cnt >= limit:
                msg = f"{symbol} disabled due to repeated slippage ({cnt})"
                log_with_tag(logger, msg)
                self.send_alert(msg, "warning")
        
    def handle_slippage(self, symbol, order_info):
        slip_pct = order_info.get("slippage_pct", 0.0)
        limit = self.config.get("SLIP_MAX", 0.15)
        if slip_pct <= limit:
            return
        self.slippage_count[symbol] = self.slippage_count.get(symbol, 0) + 1
        msg = f"Slippage {slip_pct:.2f}% for {symbol} (count {self.slippage_count[symbol]})"
        log_with_tag(logger, msg)
        if self.slippage_count[symbol] >= self.config.get("SLIP_FAIL_MAX", 5):
            self.send_alert(msg, "warning")


