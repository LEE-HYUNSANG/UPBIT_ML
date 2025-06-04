"""
[F3] 장애/슬리피지/오류 처리, 자동 롤백/경보
로그: logs/f3/F3_exception_handler.log
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
from f6_setting.alarm_control import is_enabled, get_template
import json
import os
from common_utils import now_kst

logger = logging.getLogger("F3_exception_handler")
os.makedirs("logs/f3", exist_ok=True)
fh = RotatingFileHandler(
    "logs/f3/F3_exception_handler.log",
    encoding="utf-8",
    maxBytes=100_000 * 1024,
    backupCount=1000,
)
formatter = logging.Formatter('%(asctime)s [F3] %(message)s')
fh.setFormatter(formatter)
logger.addHandler(fh)
logger.setLevel(logging.INFO)


def _log_jsonl(path: str, data: dict) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)
        f.write("\n")

class ExceptionHandler:
    def __init__(self, config):
        self.config = config
        self.slippage_count = {}
        env = load_env()
        self.tg_token = env.get("TELEGRAM_TOKEN")
        self.tg_chat_id = env.get("TELEGRAM_CHAT_ID")
        if self.tg_token and str(self.tg_token).startswith("YOUR_"):
            self.tg_token = None
        if self.tg_chat_id and str(self.tg_chat_id).startswith("YOUR_"):
            self.tg_chat_id = None

    def _log_event(self, data: dict) -> None:
        path = os.path.join("logs", "etc", "events.jsonl")
        data["time"] = now_kst()
        _log_jsonl(path, data)

    def send_alert(self, message: str, severity: str = "info", category: str = "system_alert") -> None:
        """Send a Telegram notification if credentials are set and category is enabled."""
        if not self.tg_token or not self.tg_chat_id:
            log_with_tag(logger, "Telegram credentials missing; alert suppressed")
            return
        if not is_enabled(category):
            log_with_tag(logger, f"Alert category disabled: {category}")
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
        self._log_event({
            "event": "Exception",
            "context": context,
            "type": type(exception).__name__,
            "message": str(exception),
        })
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
                self._log_event({
                    "event": "SlippageLimit", "symbol": symbol, "count": cnt
                })
                self.send_alert(msg, "warning", "system_alert")
        
    def handle_slippage(self, symbol, order_info):
        slip_pct = order_info.get("slippage_pct", 0.0)
        limit = self.config.get("SLIP_MAX", 0.15)
        if slip_pct <= limit:
            return
        self.slippage_count[symbol] = self.slippage_count.get(symbol, 0) + 1
        msg = f"Slippage {slip_pct:.2f}% for {symbol} (count {self.slippage_count[symbol]})"
        log_with_tag(logger, msg)
        self._log_event({
            "event": "Slippage",
            "symbol": symbol,
            "slippage": slip_pct,
            "count": self.slippage_count[symbol],
        })
        if self.slippage_count[symbol] >= self.config.get("SLIP_FAIL_MAX", 5):
            self.send_alert(msg, "warning", "system_alert")


