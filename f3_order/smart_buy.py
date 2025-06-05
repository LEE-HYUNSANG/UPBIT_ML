"""
[F3] 지정가 재시도 주문 함수
로그: logs/f3/F3_smart_buy.log
"""
import logging
from logging.handlers import RotatingFileHandler
from .utils import log_with_tag, tick_size
from common_utils import DedupFilter
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
logger.propagate = False
logger.addFilter(DedupFilter(60))
if os.environ.get("PYTEST_CURRENT_TEST"):
    logger.disabled = True


def _get_price(mode: str, symbol: str, client) -> float | None:
    """Fetch the current bid/ask price according to ``mode``.

    Parameters
    ----------
    mode : str
        Either ``"BID1"``, ``"BID1+"`` or ``"ASK1"`` determining which price
        to fetch. ``"BID1+"`` returns the best bid plus one tick.
    symbol : str
        Market code to query.
    client : UpbitClient
        API client used to request the orderbook.

    Returns
    -------
    float | None
        Price if available, otherwise ``None``.
    """
    try:
        ob = client.orderbook([symbol])
        if not ob:
            return None
        unit = ob[0].get("orderbook_units", [{}])[0]
        if mode.startswith("BID1"):
            price = float(unit.get("bid_price", 0))
            if mode.endswith("+"):
                price += tick_size(price)
            return price
        if mode == "ASK1":
            return float(unit.get("ask_price", 0))
    except Exception:  # pragma: no cover - network failure
        return None
    return None


def smart_buy(signal, config, position_manager=None, parent_logger=None):
    """Attempt a two-step limit buy with an optional market fallback.

    Parameters
    ----------
    signal : dict
        Buy signal dictionary containing ``symbol`` and ``price``.
    config : dict
        Configuration with limit price modes and wait times.
    position_manager : PositionManager, optional
        Manager used to place orders and track positions.
    parent_logger : logging.Logger, optional
        Logger to receive additional messages.

    Returns
    -------
    dict
        Upbit order response augmented with ``filled`` or ``canceled`` keys.
    """

    symbol = signal["symbol"]
    if position_manager is None:
        log_with_tag(logger, "No PositionManager provided to smart_buy")
        return {"filled": False, "symbol": symbol, "order_type": "limit"}

    base_price = float(signal.get("price", 0))
    mode1 = str(config.get("1st_Bid_Price", "BID1"))
    mode2 = str(config.get("2nd_Bid_Price", "ASK1"))
    price1 = _get_price(mode1, symbol, position_manager.client) or base_price
    qty = config.get("ENTRY_SIZE_INITIAL", 1) / max(price1, 1)
    qty = max(qty, 0.0001)
    wait_sec1 = int(config.get("LIMIT_WAIT_SEC_1", config.get("LIMIT_WAIT_SEC", 50)))
    wait_sec2 = int(config.get("LIMIT_WAIT_SEC_2", 0))

    res = position_manager.place_order(symbol, "bid", qty, "limit", price1)
    uuid = res.get("uuid")
    if uuid:
        time.sleep(wait_sec1)
        try:
            info = position_manager.client.order_info(uuid)
            res["filled"] = info.get("state") == "done"
        except Exception as exc:  # pragma: no cover - network failure
            log_with_tag(logger, f"order_info failed for {symbol}: {exc}")
            res["filled"] = False
        if not res.get("filled"):
            try:
                position_manager.client.cancel_order(uuid)
                res["canceled"] = True
                try:
                    position_manager._reset_buy_count(symbol)
                except Exception:  # pragma: no cover - best effort
                    pass
            except Exception as exc:  # pragma: no cover - network failure
                log_with_tag(logger, f"cancel_order failed for {uuid}: {exc}")

            if wait_sec2 > 0:
                price2 = _get_price(mode2, symbol, position_manager.client) or price1
                res2 = position_manager.place_order(symbol, "bid", qty, "limit", price2)
                uuid2 = res2.get("uuid")
                if uuid2:
                    time.sleep(wait_sec2)
                    try:
                        info2 = position_manager.client.order_info(uuid2)
                        res2["filled"] = info2.get("state") == "done"
                    except Exception as exc:  # pragma: no cover - network failure
                        log_with_tag(logger, f"order_info failed for {symbol}: {exc}")
                        res2["filled"] = False
                    if not res2.get("filled"):
                        try:
                            position_manager.client.cancel_order(uuid2)
                            res2["canceled"] = True
                            try:
                                position_manager._reset_buy_count(symbol)
                            except Exception:  # pragma: no cover - best effort
                                pass
                        except Exception as exc:  # pragma: no cover - network failure
                            log_with_tag(logger, f"cancel_order failed for {uuid2}: {exc}")
                res = res2
            elif config.get("FALLBACK_MARKET"):
                res2 = position_manager.place_order(symbol, "bid", qty, "market", None)
                uuid2 = res2.get("uuid")
                if uuid2:
                    res2["filled"] = True
                res = res2
    return res

