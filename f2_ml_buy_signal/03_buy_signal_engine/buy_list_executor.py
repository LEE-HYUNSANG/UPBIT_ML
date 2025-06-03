import json
import logging
from pathlib import Path

from f3_order.order_executor import (
    OrderExecutor,
    _default_executor,
    _buy_list_lock,
)
from f3_order.upbit_api import UpbitClient
from f3_order.utils import log_with_tag

CONFIG_DIR = Path("config")

logger = logging.getLogger("buy_list_executor")


def _load_buy_list(path: Path) -> list:
    if not path.exists():
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):
            return data
    except Exception as exc:  # pragma: no cover - best effort
        log_with_tag(logger, f"Failed to load buy list: {exc}")
    return []


def execute_buy_list(executor: OrderExecutor | None = None) -> list[str]:
    """Execute buys when ``buy_signal`` is 1 and ``buy_count`` is 0.

    Parameters
    ----------
    executor : OrderExecutor, optional
        Order executor instance to use. Defaults to the shared
        :data:`_default_executor` to avoid duplicate orders.
    """
    buy_path = CONFIG_DIR / "f2_f2_realtime_buy_list.json"
    with _buy_list_lock(buy_path):
        buy_list = _load_buy_list(buy_path)

        seen = set()
        deduped = []
        for item in buy_list:
            symbol = item.get("symbol")
            if symbol and symbol not in seen:
                deduped.append(item)
                seen.add(symbol)
        if len(deduped) != len(buy_list):
            buy_list = deduped
            log_with_tag(logger, "Removed duplicate symbols from buy list")

        targets = [
            b["symbol"]
            for b in buy_list
            if b.get("buy_signal") == 1 and b.get("buy_count", 0) == 0
        ]
        if not targets:
            log_with_tag(logger, "No buy candidates found")
            return []

        client = UpbitClient()
        oe = executor or _default_executor

        prices = {}
        try:
            ticker_info = client.ticker(targets)
            prices = {
                t["market"]: float(t.get("trade_price", 0)) for t in ticker_info
            }
        except Exception as exc:  # pragma: no cover - network issues
            log_with_tag(logger, f"Failed to fetch ticker: {exc}")

        executed = []
        for item in buy_list:
            if item.get("buy_signal") != 1:
                continue
            symbol = item.get("symbol")
            price = prices.get(symbol)
            if price is None:
                log_with_tag(logger, f"Price missing for {symbol}, skipping")
                continue
            signal = {
                "symbol": symbol,
                "buy_signal": True,
                "sell_signal": False,
                "price": price,
                "spread": 0.0,
                "buy_triggers": [],
                "sell_triggers": [],
            }
            log_with_tag(logger, f"Executing buy for {symbol} at {price}")
            oe.entry(signal)
            executed.append(symbol)
            for it in buy_list:
                if it.get("symbol") == symbol:
                    it["buy_count"] = 1
                    log_with_tag(logger, f"Updated buy_count for {symbol}")
                    break

        try:
            with open(buy_path, "w", encoding="utf-8") as f:
                json.dump(buy_list, f, ensure_ascii=False, indent=2)
        except Exception as exc:  # pragma: no cover - best effort
            log_with_tag(logger, f"Failed to save buy list: {exc}")
        return executed


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    execute_buy_list()
