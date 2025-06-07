import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
import time
from typing import Optional
from common_utils import ensure_utf8_stdout, setup_logging

from f3_order.order_executor import entry as f3_entry, _default_executor
RiskManager = None  # F4 risk management module removed
from f6_setting.remote_control import read_status

import pyupbit

from f1_universe.universe_selector import (
    get_universe,
    load_config,
    select_universe,
    schedule_universe_updates,
    load_universe_from_file,
    init_coin_positions,
)
from f2_buy_signal import check_signals


def ensure_kst(timestamp_col):
    """``timestamp_col``을 서울 시간대로 변환"""

    import pandas as pd

    ts = pd.to_datetime(timestamp_col)
    if hasattr(ts, "dt"):
        if ts.dt.tz is None:
            return ts.dt.tz_localize("Asia/Seoul")
        return ts.dt.tz_convert("Asia/Seoul")
    if ts.tzinfo is None:
        return ts.tz_localize("Asia/Seoul")
    return ts.tz_convert("Asia/Seoul")


def fetch_ohlcv(symbol: str, interval: str, count: int = 50):
    """pyupbit을 이용해 종목의 OHLCV 데이터를 가져옵니다.

    반환된 데이터프레임의 인덱스를 ``timestamp`` 컬럼으로 변환하여
    ``process_symbol``에서 ``f2_signal``에 필요한 형태로 제공합니다.
    """
    try:
        df = pyupbit.get_ohlcv(symbol, interval=interval, count=count)
        df = df.reset_index().rename(columns={"index": "timestamp"})
        if hasattr(df, "iloc") and not df.empty:
            sample = df.iloc[-1].to_dict()
            logging.info(
                f"[{symbol}] {interval} sample row: {sample}"
            )
        try:
            import pandas as pd  # noqa: F401
        except ImportError:
            pass
        else:
            if hasattr(df, "columns") and "timestamp" in df.columns:
                df["timestamp"] = ensure_kst(df["timestamp"])
        return df
    except Exception as exc:  # pragma: no cover - network access
        logging.error(f"[{symbol}] Failed to fetch {interval} data: {exc}")
        return None




def process_symbol(symbol: str) -> Optional[dict]:
    """Fetch OHLCV data for ``symbol`` and compute buy/sell signals.

    Parameters
    ----------
    symbol : str
        Market code to process.

    Returns
    -------
    dict | None
        Signal dictionary forwarded to F3 or ``None`` when data is missing.
    """
    df_1m = fetch_ohlcv(symbol, "minute1")
    if df_1m is None or df_1m.empty:
        logging.warning(f"[{symbol}] No OHLCV data available")
        return None

    logging.info(
        f"[F1-F2] process_symbol() \uc774 OHLCV \ub370\uc774\ud130\ub97c \uac00\uc838\uc654\uc2b5\ub2c8\ub2e4: {symbol}"
    )

    pm = _default_executor.position_manager
    open_pos = [p for p in pm.positions if p.get("symbol") == symbol and p.get("status") == "open"]

    signals = check_signals(symbol)
    buy_ok = not open_pos and all(signals.values())
    result = {"symbol": symbol, "buy_signal": buy_ok, "sell_signal": False, "buy_triggers": [], "sell_triggers": []}
    if getattr(df_1m, "empty", True) is False and hasattr(df_1m, "iloc") and "close" in getattr(df_1m, "columns", []):
        result["price"] = float(df_1m["close"].iloc[-1])
    logging.info(f"[F1-F2] process_symbol() signals={signals} result={buy_ok}: {symbol}")
    if result.get("buy_signal"):
        logging.info(f"[{symbol}] BUY signal triggered")
    else:
        logging.debug(f"[{symbol}] No buy signal")
    try:
        f3_entry(result)
    except Exception as exc:
        logging.error(f"[{symbol}] Failed to send signal to F3: {exc}")
    return result


def main_loop(interval: int = 1, stop_event=None) -> None:
    """Continuously compute signals for the current universe.

    Parameters
    ----------
    interval : int, optional
        Sleep time between iterations in seconds.
    stop_event : threading.Event, optional
        When set, the loop exits gracefully.
    """
    cfg = load_config()
    load_universe_from_file()
    init_coin_positions(5000.0)
    logging.info(
        "[F1-F2] signal_loop.py \uc774 current_universe.json \ud30c\uc77c\uc744 \ub85c\ub4dc \ud588\uc2b5\ub2c8\ub2e4."
    )
    schedule_universe_updates(1800, cfg)

    executor = _default_executor
    if callable(RiskManager):
        risk_manager = RiskManager(
            order_executor=executor,
            exception_handler=executor.exception_handler,
        )
        from f6_setting.buy_config import load_buy_config
        if hasattr(risk_manager, "config"):
            risk_manager.config._cache.update(load_buy_config())
        executor.set_risk_manager(risk_manager)
    else:
        risk_manager = None
    while True:
        status = read_status().upper()
        if status != "ON":
            logging.info("[Loop] Auto-trade status %s; waiting for ON...", status)
            executor.manage_positions()
            time.sleep(5)
            if stop_event and stop_event.is_set():
                break
            continue
        if stop_event and stop_event.is_set():
            break
        universe = get_universe()
        if not universe:
            universe = select_universe(cfg)
        imported = [
            p.get("symbol")
            for p in executor.position_manager.positions
            if p.get("status") == "open" and p.get("origin") == "imported"
        ]
        universe = list(dict.fromkeys(universe + imported))
        logging.info(f"[Loop] Universe: {universe}")
        executor.position_manager.sync_with_universe(universe)
        # Update risk manager with open positions
        open_syms = [
            p.get("symbol")
            for p in executor.position_manager.positions
            if p.get("status") == "open"
        ]
        if risk_manager:
            risk_manager.update_account(0.0, 0.0, 0.0, open_syms)
            risk_manager.periodic()
        for symbol in universe:
            try:
                logging.info(f"[F1-F2] process_symbol() \uc2dc\uc791: {symbol}")
                process_symbol(symbol)
            except Exception as exc:  # pragma: no cover - best effort
                logging.error(f"[{symbol}] Processing error: {exc}")
        executor.manage_positions()
        time.sleep(interval)


if __name__ == "__main__":
    ensure_utf8_stdout()
    setup_logging(
        "F1-F2",
        [
            Path("logs/etc/F1-F2_loop.log"),
            Path("logs/f1/F1_signal_engine.log"),
            Path("logs/f2/F2_signal_engine.log"),
        ],
    )
    load_universe_from_file()
    logging.info(
        "[F1-F2] signal_loop.py \uc774 current_universe.json \ud30c\uc77c\uc744 \ub85c\ub4dc \ud588\uc2b5\ub2c8\ub2e4."
    )
    main_loop()
