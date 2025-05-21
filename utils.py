import json
import logging
import os
import sys
from typing import Iterable
import time

import pandas as pd
import requests
import pyupbit


# Custom log level for detailed calculations
CAL_LEVEL = 15
logging.addLevelName(CAL_LEVEL, "CAL")


def _cal(self, message, *args, **kwargs) -> None:
    """Log 'message' with level 'CAL'."""
    if self.isEnabledFor(CAL_LEVEL):
        self._log(CAL_LEVEL, message, args, **kwargs)


logging.Logger.cal = _cal


def cal(message: str, *args, **kwargs) -> None:
    """Module level CAL log."""
    logging.log(CAL_LEVEL, message, *args, **kwargs)


class LevelFilter(logging.Filter):
    """Filter to allow only records of a specific level."""

    def __init__(self, level: int) -> None:
        super().__init__()
        self.level = level

    def filter(self, record: logging.LogRecord) -> bool:  # type: ignore[override]
        return record.levelno == self.level


def setup_logging(level: str | None = None, log_dir: str = "logs") -> logging.Logger:
    """로그 파일과 콘솔 출력을 설정한다."""
    if level is None:
        level = os.getenv("LOG_LEVEL", "INFO")
    numeric_level = getattr(logging, level.upper(), logging.INFO)
    logger = logging.getLogger()
    logger.setLevel(numeric_level)
    if not logger.handlers:
        os.makedirs(log_dir, exist_ok=True)
        fmt = logging.Formatter(
            "[%(levelname)s][%(asctime)s][%(name)s] %(message)s",
            "%Y-%m-%d %H:%M:%S",
        )
        files = [
            ("debug", logging.DEBUG),
            ("cal", CAL_LEVEL),
            ("info", logging.INFO),
            ("warning", logging.WARNING),
            ("error", logging.ERROR),
            ("critical", logging.CRITICAL),
        ]
        for name, lvl in files:
            fh = logging.FileHandler(os.path.join(log_dir, f"{name}.log"), encoding="utf-8")
            fh.setFormatter(fmt)
            fh.setLevel(lvl)
            fh.addFilter(LevelFilter(lvl))
            logger.addHandler(fh)
        sh = logging.StreamHandler()
        sh.setFormatter(fmt)
        sh.setLevel(logging.INFO)
        logger.addHandler(sh)
    return logger


def send_telegram(token: str, chat_id: str, text: str) -> None:
    """텔레그램 봇 API로 메시지를 보낸다."""
    try:
        logging.debug("Sending telegram message", extra={"chat_id": chat_id})
        resp = requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            data={"chat_id": chat_id, "text": text},
            timeout=5,
        )
        logging.debug("Telegram response %s", resp.status_code)
        logging.info("Telegram message sent")
    except Exception as e:
        logging.exception("Telegram send failed: %s", e)


def load_secrets(
    path: str = "config/secrets.json",
    required: Iterable[str] = (
        "UPBIT_KEY",
        "UPBIT_SECRET",
        "TELEGRAM_TOKEN",
    ),
) -> dict:
    """지정된 경로에서 시크릿 정보를 읽어 필수 키가 있는지 확인한다.

    파일이 없거나 형식이 잘못되었거나 필수 키가 비어 있으면 오류를 출력하고
    로그를 남긴 뒤 프로그램을 종료한다. 텔레그램 설정이 존재하면 동일한 메시지를
    텔레그램으로도 전송한다.
    """

    def alert(msg: str, secrets: dict | None = None) -> None:
        print(msg)
        logging.error(msg)
        token = os.getenv("TELEGRAM_TOKEN")
        chat = os.getenv("TELEGRAM_CHAT_ID")
        if secrets:
            token = secrets.get("TELEGRAM_TOKEN", token)
            chat = secrets.get("TELEGRAM_CHAT_ID", chat)
        if token and chat:
            send_telegram(token, chat, msg)

    try:
        with open(path, encoding="utf-8") as f:
            secrets = json.load(f)
    except FileNotFoundError:
        alert(f"[ERROR] Required file '{path}' not found.")
        sys.exit(1)
    except PermissionError:
        alert(f"[ERROR] No permission to read '{path}'.")
        sys.exit(1)
    except json.JSONDecodeError as e:
        alert(f"[ERROR] Failed to parse '{path}': {e}")
        sys.exit(1)

    missing = [key for key in required if not secrets.get(key)]
    if missing:
        alert(f"[ERROR] Missing required secrets: {', '.join(missing)}", secrets)
        sys.exit(1)

    logging.info("Secrets loaded from %s", path)
    return secrets


def _fetch_ticks(ticker: str, count: int) -> list[dict]:
    """pyupbit에 get_ticks가 없을 때 REST API로 대체 요청한다."""
    url = "https://api.upbit.com/v1/trades/ticks"
    params = {"market": ticker, "count": count}
    resp = requests.get(url, params=params, timeout=5)
    resp.raise_for_status()
    return resp.json()


def calc_tis(ticker: str, minutes: int = 5, count: int = 200) -> float | None:
    """체결강도(TIS)를 계산해 반환한다.

    ``minutes`` 값은 매수/매도 체결량을 합산할 기간(분)을 의미하며,
    ``count`` 는 업비트에서 가져올 틱 데이터 개수(최대 200)를 지정한다.
    API 요청에 실패하면 ``None`` 을 반환한다.
    """
    cal("calc_tis start for %s", ticker)
    try:
        if hasattr(pyupbit, "get_ticks"):
            ticks = pyupbit.get_ticks(ticker, count=count)
        else:
            ticks = _fetch_ticks(ticker, count)
        if not ticks:
            cal("calc_tis no tick data for %s", ticker)
            raise ValueError("no ticks")
        df = pd.DataFrame(ticks)
        cutoff = int((time.time() - minutes * 60) * 1000)
        recent = df[df["timestamp"] >= cutoff]
        if recent.empty:
            cal("calc_tis no recent ticks for %s", ticker)
        buy_qty = recent[recent["ask_bid"] == "BID"]["trade_volume"].sum()
        sell_qty = recent[recent["ask_bid"] == "ASK"]["trade_volume"].sum()
        tis = (buy_qty / sell_qty) * 100 if sell_qty > 0 else 0.0
        cal("[TIS] %s buy=%.2f sell=%.2f tis=%.2f", ticker, buy_qty, sell_qty, tis)
        if ticker.endswith("-XPR"):
            logging.info("[TIS] XPR buy=%.2f sell=%.2f tis=%.2f", buy_qty, sell_qty, tis)
        return tis
    except Exception as e:  # API or parsing error
        cal("calc_tis failed for %s: %s", ticker, e)
        try:
            ob = pyupbit.get_orderbook(ticker)
            if not ob:
                cal("calc_tis no orderbook for %s", ticker)
                return None
            book = ob[0]
            bid = float(book.get("total_bid_size", 0))
            ask = float(book.get("total_ask_size", 0))
            if ask == 0:
                cal("calc_tis ask size zero for %s", ticker)
                return None
            tis = (bid / ask) * 100
            cal("[TIS-FB] %s orderbook tis=%.2f", ticker, tis)
            return tis
        except Exception as e2:
            cal("calc_tis fallback failed for %s: %s", ticker, e2)
            return None


def load_market_signals(path: str = "config/market.json") -> list[dict]:
    """지정된 파일에서 시장 신호 데이터를 읽어 목록으로 반환한다.

    파일에는 최소한 ``coin``, ``price``, ``rank`` 키가 포함된 객체 리스트가 들어 있어야 하며,
    파일이 없거나 형식이 잘못되었을 경우 빈 리스트를 반환한다.
    """
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, list):
            raise ValueError("market data must be a list")
        return data
    except FileNotFoundError:
        logging.warning("Market file not found: %s", path)
    except Exception as e:  # json error or validation error
        logging.error("Failed to load market file %s: %s", path, e)
    return []

def load_filter_settings(path: str = "config/filter.json") -> dict:
    """filter.json을 읽어 필터 설정 dict로 반환한다.

    파일이 없거나 읽기 오류가 나면 기본값을 제공한다.
    """
    defaults = {"min_price": 0, "max_price": 9e14, "rank": 30}
    if not os.path.exists(path):
        return defaults
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        for k, v in defaults.items():
            data.setdefault(k, v)
        return data
    except Exception:
        logging.warning("Failed to load filter file: %s", path)
        return defaults

