# -*- coding: utf-8 -*-
"""하이브리드 매수/매도 로직 모음.

매수와 매도 모두 호가 스프레드를 고려해 시장가와 지정가를
적절히 혼합한다. 스프레드가 설정값 이하이면 시장가를 사용하고
그 외에는 한 틱 아래(혹은 위) IOC 지정가 주문을 재시도한다.
명확한 실패가 반복되면 최종적으로 시장가 주문으로 전환한다.
각 함수는 평균 체결가와 체결 수량을 반환한다.
"""

from __future__ import annotations

import logging
import time
from typing import Tuple

import pyupbit

logger = logging.getLogger(__name__)


def _tick_size(price: float) -> float:
    """업비트 호가 단위를 계산한다."""
    steps = [
        (10, 0.01),
        (100, 0.1),
        (1000, 1),
        (10000, 5),
        (100000, 10),
        (500000, 50),
        (1000000, 100),
        (2000000, 500),
    ]
    for bound, tick in steps:
        if price < bound:
            return tick
    return 1000


def _fetch_spread(ticker: str) -> Tuple[float, float, float]:
    """호가창에서 매수호가, 매도호가, 스프레드 비율을 반환한다."""
    book = pyupbit.get_orderbook(ticker)[0]["orderbook_units"][0]
    ask = float(book["ask_price"])
    bid = float(book["bid_price"])
    spread = (ask - bid) / ask
    return ask, bid, spread


def smart_buy(
    upbit: pyupbit.Upbit,
    ticker: str,
    total_krw: float,
    slippage: float = 0.001,
    max_retries: int = 3,
    slippage_limit: float | None = None,
) -> Tuple[float, float]:
    """호가 스프레드를 고려한 하이브리드 매수 주문."""
    for attempt in range(max_retries):
        try:
            ask, bid, spread = _fetch_spread(ticker)
            if slippage_limit is not None and spread > slippage_limit:
                logger.warning(
                    "[BUY] skip %s spread %.6f limit %.6f",
                    ticker,
                    spread,
                    slippage_limit,
                )
                return 0.0, 0.0
            if spread <= slippage:
                res = upbit.buy_market_order(ticker, total_krw)
                price = float(res.get("price", ask))
                vol = float(res.get("volume", total_krw / price))
                logger.info("[BUY] market %s price=%s vol=%s", ticker, price, vol)
                return price, vol
            tick = _tick_size(ask)
            limit_price = ask - tick
            vol = total_krw / limit_price
            res = upbit.buy_limit_order(ticker, limit_price, vol)
            if res.get("status") == "done":
                logger.info("[BUY] limit %s price=%s vol=%s", ticker, limit_price, vol)
                return limit_price, vol
        except Exception as e:  # pragma: no cover - logging only
            logger.warning("smart_buy retry %s %s", attempt + 1, e)
            time.sleep(0.2)
    res = upbit.buy_market_order(ticker, total_krw)
    price = float(res.get("price", 0))
    vol = float(res.get("volume", 0))
    logger.info("[BUY] fallback market %s price=%s vol=%s", ticker, price, vol)
    return price, vol


def smart_sell(
    upbit: pyupbit.Upbit,
    ticker: str,
    quantity: float,
    slippage: float = 0.001,
    max_retries: int = 3,
    split: int = 1,
    slippage_limit: float | None = None,
) -> Tuple[float, float]:
    """호가 스프레드를 고려한 하이브리드 매도 주문."""
    remain = quantity
    avg_price = 0.0
    sold = 0.0
    for _ in range(split):
        part = remain / (split - sold / remain) if split > 1 else remain
        for attempt in range(max_retries):
            try:
                ask, bid, spread = _fetch_spread(ticker)
                if slippage_limit is not None and spread > slippage_limit:
                    logger.warning(
                        "[SELL] skip %s spread %.6f limit %.6f",
                        ticker,
                        spread,
                        slippage_limit,
                    )
                    return avg_price, sold
                if spread <= slippage:
                    res = upbit.sell_market_order(ticker, part)
                    price = float(res.get("price", bid))
                    qty = float(res.get("volume", part))
                    avg_price = ((avg_price * sold) + price * qty) / (sold + qty)
                    sold += qty
                    logger.info(
                        "[SELL] market %s price=%s vol=%s", ticker, price, qty
                    )
                    break
                tick = _tick_size(bid)
                limit_price = bid + tick
                res = upbit.sell_limit_order(ticker, limit_price, part)
                if res.get("status") == "done":
                    avg_price = (
                        (avg_price * sold) + limit_price * part
                    ) / (sold + part)
                    sold += part
                    logger.info(
                        "[SELL] limit %s price=%s vol=%s", ticker, limit_price, part
                    )
                    break
            except Exception as e:  # pragma: no cover - logging only
                logger.warning("smart_sell retry %s %s", attempt + 1, e)
                time.sleep(0.2)
        else:
            res = upbit.sell_market_order(ticker, part)
            price = float(res.get("price", 0))
            qty = float(res.get("volume", part))
            avg_price = ((avg_price * sold) + price * qty) / (sold + qty)
            sold += qty
            logger.info(
                "[SELL] fallback market %s price=%s vol=%s", ticker, price, qty
            )
    return avg_price, sold


def run_trading_bot(
    upbit: pyupbit.Upbit,
    ticker: str,
    buy_signal: bool,
    sell_signal: bool,
    total_krw: float,
    quantity: float,
) -> None:
    """매매 시그널에 따라 smart_buy/sell 을 호출한다."""
    if buy_signal:
        smart_buy(upbit, ticker, total_krw)
    if sell_signal:
        smart_sell(upbit, ticker, quantity)
