"""
[F3] 지정가 재시도 주문 함수
로그: logs/f3/F3_smart_buy.log
"""
import logging
from logging.handlers import RotatingFileHandler
from .utils import log_with_tag
import time
import os

logger = logging.getLogger("F3_smart_buy")
os.makedirs("logs/f3", exist_ok=True)
fh = RotatingFileHandler(
    "logs/f3/F3_smart_buy.log",
    encoding="utf-8",
    maxBytes=100_000 * 1024,
    backupCount=1000,
)
formatter = logging.Formatter('%(asctime)s [F3] %(message)s')
fh.setFormatter(formatter)
logger.addHandler(fh)
logger.setLevel(logging.INFO)


def smart_buy(signal, config, position_manager=None, parent_logger=None):
    """Place a limit buy order and wait once for it to fill."""

    symbol = signal["symbol"]
    if position_manager is None:
        log_with_tag(logger, "No PositionManager provided to smart_buy")
        return {"filled": False, "symbol": symbol, "order_type": "limit"}

    price = float(signal.get("price", 0))
    qty = config.get("ENTRY_SIZE_INITIAL", 1) / max(price, 1)
    qty = max(qty, 0.0001)
    wait_sec = int(config.get("LIMIT_WAIT_SEC", 50))

    res = position_manager.place_order(symbol, "bid", qty, "limit", price)
    uuid = res.get("uuid")
    if uuid:
        time.sleep(wait_sec)
        try:
            info = position_manager.client.order_info(uuid)
            res["filled"] = info.get("state") == "done"
        except Exception as exc:  # pragma: no cover - network failure
            log_with_tag(logger, f"order_info failed for {symbol}: {exc}")
            res["filled"] = False
        if not res.get("filled"):
            try:
                position_manager.client.cancel_order(uuid)
            except Exception as exc:  # pragma: no cover - network failure
                log_with_tag(logger, f"cancel_order failed for {uuid}: {exc}")
    return res

