import logging
import time
from typing import Optional

import pyupbit

from f1_universe import (
    get_universe,
    load_config,
    select_universe,
    schedule_universe_updates,
    load_universe_from_file,
)
from f2_signal import f2_signal


def fetch_ohlcv(symbol: str, interval: str, count: int = 50):
    """Fetch OHLCV data for a symbol using pyupbit."""
    try:
        return pyupbit.get_ohlcv(symbol, interval=interval, count=count)
    except Exception as exc:  # pragma: no cover - network access
        logging.error(f"[{symbol}] Failed to fetch {interval} data: {exc}")
        return None


def process_symbol(symbol: str) -> Optional[dict]:
    """Fetch data for a symbol and run f2_signal."""
    df_1m = fetch_ohlcv(symbol, "minute1")
    df_5m = fetch_ohlcv(symbol, "minute5")
    if df_1m is None or df_5m is None or df_1m.empty or df_5m.empty:
        logging.warning(f"[{symbol}] No OHLCV data available")
        return None
    result = f2_signal(df_1m, df_5m, symbol)
    if result.get("buy_signal") or result.get("sell_signal"):
        logging.info(
            f"[{symbol}] BUY={result['buy_signal']} SELL={result['sell_signal']}"
        )
    else:
        logging.debug(f"[{symbol}] No signal")
    return result


def main_loop(interval: int = 30) -> None:
    """Main processing loop fetching the universe and evaluating signals."""
    cfg = load_config()
    load_universe_from_file()
    schedule_universe_updates(1800, cfg)
    while True:
        universe = get_universe()
        if not universe:
            universe = select_universe(cfg)
        logging.info(f"[Loop] Universe: {universe}")
        for symbol in universe:
            try:
                process_symbol(symbol)
            except Exception as exc:  # pragma: no cover - best effort
                logging.error(f"[{symbol}] Processing error: {exc}")
        time.sleep(interval)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [F1F2] [%(levelname)s] %(message)s",
        handlers=[
            logging.FileHandler("logs/F1F2_loop.log", encoding="utf-8"),
            logging.StreamHandler(),
        ],
    )
    load_universe_from_file()
    main_loop()
