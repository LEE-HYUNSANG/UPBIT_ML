"""
[F3] 하이브리드 주문 함수 (시장가↔IOC, 체결률/슬리피지 최적화)
로그: logs/F3_smart_buy.log
"""
import logging
from logging.handlers import RotatingFileHandler
from .utils import log_with_tag

logger = logging.getLogger("F3_smart_buy")
fh = RotatingFileHandler(
    "logs/F3_smart_buy.log",
    encoding="utf-8",
    maxBytes=100_000 * 1024,
    backupCount=1000,
)
formatter = logging.Formatter('%(asctime)s [F3] %(message)s')
fh.setFormatter(formatter)
logger.addHandler(fh)
logger.setLevel(logging.INFO)


def smart_buy(signal, config, position_manager=None, parent_logger=None):
    """Execute a real buy order using ``position_manager``.

    ``position_manager`` must provide a ``place_order`` method compatible with
    :meth:`f3_order.position_manager.PositionManager.place_order`.
    The function falls back to a market order when IOC attempts fail.
    """

    symbol = signal["symbol"]
    spread = float(signal.get("spread", 0.0))
    SPREAD_TH = config.get("SPREAD_TH", 0.0008)
    MAX_RETRY = config.get("MAX_RETRY", 2)

    if position_manager is None:
        log_with_tag(logger, "No PositionManager provided to smart_buy")
        return {"filled": False, "symbol": symbol, "order_type": "market"}

    qty = config.get("ENTRY_SIZE_INITIAL", 1) / max(float(signal.get("price", 1)), 1)
    qty = max(qty, 0.0001)

    # Try IOC first if spread is wide
    for attempt in range(MAX_RETRY + 1):
        if spread <= SPREAD_TH or attempt == MAX_RETRY:
            # Upbit uses "bid" for buy orders
            res = position_manager.place_order(symbol, "bid", qty, "market", signal.get("price"))
            if res.get("filled"):
                log_with_tag(logger, f"Market order executed for {symbol} (spread: {spread}, attempt: {attempt})")
            else:
                log_with_tag(logger, f"Market order failed for {symbol} (spread: {spread}, attempt: {attempt})")
            return res
        else:
            res = position_manager.place_order(symbol, "bid", qty, "price", signal.get("price"))
            log_with_tag(logger, f"IOC order for {symbol} (attempt {attempt+1})")
            if res.get("filled"):
                return res

    log_with_tag(logger, f"Fallback to market order for {symbol}")
    return position_manager.place_order(symbol, "bid", qty, "market", signal.get("price"))

