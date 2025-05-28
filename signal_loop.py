import logging
from logging.handlers import RotatingFileHandler
import time
from typing import Optional

from f3_order.order_executor import entry as f3_entry, _default_executor
from f4_riskManager import RiskManager

import pyupbit

from f1_universe.universe_selector import (
    get_universe,
    load_config,
    select_universe,
    schedule_universe_updates,
    load_universe_from_file,
    init_coin_positions,
)
from f2_signal.signal_engine import f2_signal


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
    """종목 데이터를 받아 f2_signal 함수 실행"""
    df_1m = fetch_ohlcv(symbol, "minute1")
    df_5m = fetch_ohlcv(symbol, "minute5")
    if df_1m is None or df_5m is None or df_1m.empty or df_5m.empty:
        logging.warning(f"[{symbol}] No OHLCV data available")
        return None

    logging.info(
        f"[F1-F2] process_symbol() \uc774 OHLCV \ub370\uc774\ud130\ub97c \uac00\uc838\uc654\uc2b5\ub2c8\ub2e4: {symbol}"
    )

    pm = _default_executor.position_manager
    open_pos = [p for p in pm.positions if p.get("symbol") == symbol and p.get("status") == "open"]
    strat_codes = [p.get("strategy") for p in open_pos if p.get("strategy")]
    result = f2_signal(
        df_1m,
        df_5m,
        symbol,
        calc_buy=not open_pos,
        calc_sell=bool(open_pos),
        strategy_codes=strat_codes or None,
    )
    logging.info(f"[F1-F2] process_symbol() \uac01 \uc2ec\ubd80\uc5d0 \ub300\ud55c f2_signal() \ud638\ucd9c\uc774 \uc644\ub8cc\ub418\uc5c8\uc2b5\ub2c8\ub2e4: {symbol}")
    if result.get("buy_signal") or result.get("sell_signal"):
        logging.info(
            f"[{symbol}] BUY={result['buy_signal']} SELL={result['sell_signal']}"
        )
    else:
        logging.debug(f"[{symbol}] No signal")

    # Forward the resulting signal to F3
    try:
        f3_entry(result)
    except Exception as exc:  # pragma: no cover - best effort
        logging.error(f"[{symbol}] Failed to send signal to F3: {exc}")

    if result.get("sell_signal") and open_pos:
        for strat_code in result.get("sell_triggers", []):
            for pos in list(open_pos):
                if pos.get("strategy") == strat_code:
                    pm.execute_sell(pos, "strategy_exit")

    return result


def main_loop(interval: int = 1, stop_event=None) -> None:
    """유니버스를 주기적으로 조회해 신호를 계산하는 메인 루프"""
    cfg = load_config()
    load_universe_from_file()
    init_coin_positions(5000.0)
    logging.info("[F1-F2] signal_loop.py \uc774 current_universe.json \ud30c\uc77c\uc744 \ub85c\ub4dc \ud588\uc2b5\ub2c8\ub2e4.")
    schedule_universe_updates(1800, cfg)

    executor = _default_executor
    risk_manager = RiskManager(order_executor=executor, exception_handler=executor.exception_handler)
    executor.set_risk_manager(risk_manager)
    while True:
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
        open_syms = [p.get("symbol") for p in executor.position_manager.positions if p.get("status") == "open"]
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
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [F1-F2] [%(levelname)s] %(message)s",
        handlers=[
            RotatingFileHandler(
                "logs/F1-F2_loop.log",
                encoding="utf-8",
                maxBytes=100_000 * 1024,
                backupCount=1000,
            ),
            RotatingFileHandler(
                "logs/F1_signal_engine.log",
                encoding="utf-8",
                maxBytes=100_000 * 1024,
                backupCount=1000,
            ),
            RotatingFileHandler(
                "logs/F2_signal_engine.log",
                encoding="utf-8",
                maxBytes=100_000 * 1024,
                backupCount=1000,
            ),
            logging.StreamHandler(),
        ],
        force=True,
    )
    load_universe_from_file()
    logging.info("[F1-F2] signal_loop.py \uc774 current_universe.json \ud30c\uc77c\uc744 \ub85c\ub4dc \ud588\uc2b5\ub2c8\ub2e4.")
    main_loop()
