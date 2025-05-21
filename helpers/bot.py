# -*- coding: utf-8 -*-
"""Simple autonomous trading loop."""

from __future__ import annotations

import json
import logging
import os
import time
from typing import Dict

import pyupbit

from utils import load_filter_settings, load_market_signals
from helpers.strategies import check_buy_signal, check_sell_signal
from helpers.execution import smart_buy, smart_sell
from helpers.utils.funds import load_fund_settings
from helpers.utils.risk import (
    load_risk_settings,
    load_manual_sells,
    save_manual_sells,
)

logger = logging.getLogger(__name__)


def load_strategy_settings(path: str = "config/strategy.json") -> Dict[str, str]:
    """Read strategy settings or fallback to config.json."""
    defaults = {"strategy": "M-BREAK", "level": "중도적"}
    file_path = path if os.path.exists(path) else "config/config.json"
    try:
        with open(file_path, encoding="utf-8") as f:
            data = json.load(f)
        defaults["strategy"] = data.get("strategy", defaults["strategy"])
        defaults["level"] = data.get("level", defaults["level"])
    except Exception:
        logger.warning("Failed to load strategy settings from %s", file_path)
    return defaults


def get_filtered_tickers(filter_conf: Dict[str, float]) -> list[str]:
    """Return list of KRW tickers filtered by price and rank."""
    min_p = float(filter_conf.get("min_price", 0) or 0)
    max_p = float(filter_conf.get("max_price", 0) or 0)
    rank = int(filter_conf.get("rank", 0) or 0)
    signals = load_market_signals()
    tickers: list[str] = []
    for s in signals:
        price = float(s.get("price", 0))
        if min_p and price < min_p:
            continue
        if max_p and max_p > 0 and price > max_p:
            continue
        tickers.append(f"KRW-{s.get('coin')}")
        if rank and len(tickers) >= rank:
            break
    return tickers


def run_trading_bot(upbit: pyupbit.Upbit, interval: float = 3.0) -> None:
    """Main trading loop integrating strategy checks and execution."""
    filter_conf = load_filter_settings()
    strategy_conf = load_strategy_settings()
    fund_conf = load_fund_settings()
    risk_conf = load_risk_settings()
    active_trades: Dict[str, Dict[str, float]] = {}
    last_reload = time.time()
    logger.info("[BOT] starting trading loop")

    while True:
        try:
            now = time.time()
            manual = load_manual_sells()
            for m in manual:
                pos = active_trades.get(m)
                if not pos:
                    continue
                avg, vol = smart_sell(
                    upbit,
                    m,
                    pos["qty"],
                    fund_conf.get("slippage_tolerance", 0.001),
                )
                logger.info("[BOT] manual sold %s avg=%.8f qty=%.6f", m, avg, vol)
                active_trades.pop(m, None)
            if manual:
                save_manual_sells([])
            if now - last_reload > 300:
                filter_conf = load_filter_settings()
                strategy_conf = load_strategy_settings()
                fund_conf = load_fund_settings()
                risk_conf = load_risk_settings()
                last_reload = now
                logger.info("[BOT] config reloaded")

            filtered = get_filtered_tickers(filter_conf)
            logger.debug("[BOT] tickers %s", filtered)

            for ticker in filtered:
                if ticker in active_trades:
                    continue
                if len(active_trades) >= fund_conf.get("max_concurrent_trades", 1):
                    logger.debug("[BOT] max concurrent trades reached")
                    break
                strat = strategy_conf.get("strategy", "M-BREAK")
                level = strategy_conf.get("level", "중도적")
                if check_buy_signal(strat, ticker, level):
                    price, qty = smart_buy(
                        upbit,
                        ticker,
                        fund_conf.get("buy_amount", 0),
                        fund_conf.get("slippage_tolerance", 0.001),
                    )
                    if qty > 0:
                        active_trades[ticker] = {
                            "buy_price": price,
                            "qty": qty,
                            "strategy": strat,
                            "level": level,
                        }
                        logger.info(
                            "[BOT] bought %s price=%.8f qty=%.6f", ticker, price, qty
                        )

            for ticker, pos in list(active_trades.items()):
                if check_sell_signal(
                    pos["strategy"],
                    ticker,
                    pos["buy_price"],
                    pos["level"],
                    risk_conf,
                ):
                    avg, vol = smart_sell(
                        upbit,
                        ticker,
                        pos["qty"],
                        fund_conf.get("slippage_tolerance", 0.001),
                    )
                    logger.info(
                        "[BOT] sold %s avg=%.8f qty=%.6f", ticker, avg, vol
                    )
                    active_trades.pop(ticker, None)

        except Exception as e:  # pragma: no cover - runtime loop
            logger.exception("[BOT] error %s", e)
        time.sleep(interval)
