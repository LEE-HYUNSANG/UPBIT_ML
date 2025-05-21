# -*- coding: utf-8 -*-
"""하이브리드 매수/매도 로직 모음.

매수와 매도 모두 호가 스프레드를 고려해 시장가와 지정가를
적절히 혼합한다. 스프레드가 설정값 이하이면 시장가를 사용하고
그 외에는 한 틱 아래(혹은 위) IOC 지정가 주문을 재시도한다.
명확한 실패가 반복되면 최종적으로 시장가 주문으로 전환한다.
각 함수는 평균 체결가와 체결 수량을 반환한다.
"""

from __future__ import annotations

import json
import logging
import os
import time
from typing import Tuple

import pyupbit

from utils import send_telegram

logger = logging.getLogger(__name__)

try:
    with open("config/secrets.json", encoding="utf-8") as f:
        _SEC = json.load(f)
    _TOKEN = _SEC.get("TELEGRAM_TOKEN")
    _CHAT = _SEC.get("TELEGRAM_CHAT_ID")
except Exception:  # pragma: no cover - file issues
    _TOKEN = os.getenv("TELEGRAM_TOKEN")
    _CHAT = os.getenv("TELEGRAM_CHAT_ID")


def _alert(msg: str) -> None:
    """텔레그램으로 오류 메시지를 전송한다."""
    if _TOKEN and _CHAT:
        try:
            send_telegram(_TOKEN, _CHAT, msg)
        except Exception:  # pragma: no cover - network
            logger.debug("telegram send failed")


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
    try:
        book = pyupbit.get_orderbook(ticker)[0]["orderbook_units"][0]
        ask = float(book["ask_price"])
        bid = float(book["bid_price"])
        spread = (ask - bid) / ask
        return ask, bid, spread
    except Exception as e:
        logger.error("[API Exception] orderbook fail %s %s", ticker, e)
        _alert(f"[API Exception] 호가 조회 실패: {ticker} {e}")
        raise


def check_filled_amount(upbit: pyupbit.Upbit, uuid: str) -> float:
    """주문 UUID로 실제 체결 수량을 반환한다."""
    try:
        order = upbit.get_order(uuid)
        if not order:
            return 0.0
        return float(order.get("executed_volume", 0.0))
    except Exception as e:  # pragma: no cover - API fail
        logger.error("[API Exception] get_order fail %s", e)
        _alert(f"[API Exception] 주문 조회 실패: {e}")
        return 0.0


def is_filled(upbit: pyupbit.Upbit, uuid: str) -> bool:
    """주문이 완전히 체결되었는지 확인한다."""
    try:
        order = upbit.get_order(uuid)
        if not order:
            return False
        return float(order.get("remaining_volume", 0.0)) == 0.0
    except Exception as e:  # pragma: no cover - API fail
        logger.error("[API Exception] order status fail %s", e)
        _alert(f"[API Exception] 주문 상태 조회 실패: {e}")
        return False


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
                vol = float(res.get("volume", total_krw / (price or 1)))
                uuid = res.get("uuid")
                if uuid:
                    for _ in range(3):
                        if is_filled(upbit, uuid):
                            vol = check_filled_amount(upbit, uuid)
                            break
                        time.sleep(1)
                logger.info("[BUY] market %s price=%s vol=%s", ticker, price, vol)
                return price, vol
            tick = _tick_size(ask)
            limit_price = ask - tick
            vol = total_krw / limit_price
            res = upbit.buy_limit_order(ticker, limit_price, vol)
            uuid = res.get("uuid")
            if res.get("status") == "done" or (uuid and is_filled(upbit, uuid)):
                if uuid:
                    vol = check_filled_amount(upbit, uuid)
                logger.info("[BUY] limit %s price=%s vol=%s", ticker, limit_price, vol)
                return limit_price, vol
        except Exception as e:
            logger.error("[ORDER FAIL] smart_buy %s %s", ticker, e)
            _alert(f"[ORDER FAIL] 매수 실패 {ticker}: {e}")
            if "잔액" in str(e) or "balance" in str(e):
                return 0.0, 0.0
            time.sleep(1)
    _alert(f"[ORDER FAIL] 매수 포기 {ticker}")
    try:
        res = upbit.buy_market_order(ticker, total_krw)
        price = float(res.get("price", 0))
        vol = float(res.get("volume", 0))
    except Exception as e:  # pragma: no cover - final
        logger.error("[ORDER FAIL] fallback buy %s", e)
        _alert(f"[ORDER FAIL] 최종 매수 실패 {ticker}: {e}")
        return 0.0, 0.0
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
                    uuid = res.get("uuid")
                    if uuid:
                        for _ in range(3):
                            if is_filled(upbit, uuid):
                                qty = check_filled_amount(upbit, uuid)
                                break
                            time.sleep(1)
                    avg_price = ((avg_price * sold) + price * qty) / (sold + qty)
                    sold += qty
                    logger.info(
                        "[SELL] market %s price=%s vol=%s", ticker, price, qty
                    )
                    break
                tick = _tick_size(bid)
                limit_price = bid + tick
                res = upbit.sell_limit_order(ticker, limit_price, part)
                uuid = res.get("uuid")
                done = res.get("status") == "done" or (uuid and is_filled(upbit, uuid))
                if done:
                    if uuid:
                        part = check_filled_amount(upbit, uuid)
                    avg_price = ((avg_price * sold) + limit_price * part) / (sold + part)
                    sold += part
                    logger.info(
                        "[SELL] limit %s price=%s vol=%s", ticker, limit_price, part
                    )
                    break
            except Exception as e:  # pragma: no cover - logging only
                logger.error("[ORDER FAIL] smart_sell %s %s", ticker, e)
                _alert(f"[ORDER FAIL] 매도 실패 {ticker}: {e}")
                if "잔액" in str(e) or "balance" in str(e):
                    return avg_price, sold
                time.sleep(1)
        else:
            res = upbit.sell_market_order(ticker, part)
            price = float(res.get("price", 0))
            qty = float(res.get("volume", part))
            uuid = res.get("uuid")
            if uuid and is_filled(upbit, uuid):
                qty = check_filled_amount(upbit, uuid)
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
