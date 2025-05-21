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


def ask_tick(price: float) -> float:
    """업비트 호가 한 틱을 계산한다."""
    if price < 10:
        return 1
    elif price < 100:
        return 5
    elif price < 1000:
        return 10
    elif price < 10000:
        return 50
    elif price < 100000:
        return 100
    else:
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


def check_filled_amount(uuid: str) -> float:
    """주문 UUID로 체결된 수량을 조회한다."""
    try:
        order = pyupbit.get_order(uuid)
        if not order:
            return 0.0
        return float(order.get("executed_volume", 0.0))
    except Exception as e:  # pragma: no cover - API fail
        logger.error("[API Exception] get_order fail %s", e)
        _alert(f"[API Exception] 주문 조회 실패: {e}")
        return 0.0


def is_filled(uuid: str) -> bool:
    """주문이 전량 체결되었는지 확인한다."""
    try:
        order = pyupbit.get_order(uuid)
        if not order:
            return False
        return order.get("state") == "done" and float(order.get("remaining", 0)) == 0
    except Exception as e:  # pragma: no cover - API fail
        logger.error("[API Exception] order status fail %s", e)
        _alert(f"[API Exception] 주문 상태 조회 실패: {e}")
        return False


def smart_buy(
    upbit: pyupbit.Upbit,
    ticker: str,
    total_krw: float,
    slippage_limit: float = 0.0008,
    max_retry: int = 2,
) -> Tuple[float, float]:
    """스프레드에 따라 시장가 또는 지정가 매수를 시도한다."""
    for attempt in range(max_retry):
        try:
            ask, bid, spread = _fetch_spread(ticker)
            if spread <= slippage_limit:
                res = upbit.buy_market_order(ticker, total_krw)
                price = float(res.get("price", ask))
                qty = float(res.get("volume", total_krw / price))
                uuid = res.get("uuid")
                if uuid and not is_filled(uuid):
                    qty = check_filled_amount(uuid)
                logger.info("[BUY] market %s %.6f %.6f", ticker, price, qty)
                return price, qty
            tick = ask_tick(ask)
            limit_price = ask - tick
            qty = total_krw / limit_price
            res = upbit.buy_limit_order(ticker, limit_price, qty)
            uuid = res.get("uuid")
            time.sleep(0.5)
            if uuid and is_filled(uuid):
                qty = check_filled_amount(uuid)
                logger.info("[BUY] limit %s %.6f %.6f", ticker, limit_price, qty)
                return limit_price, qty
        except Exception as e:
            logger.error("[ORDER FAIL] smart_buy %s %s", ticker, e)
            _alert(f"[ORDER FAIL] 매수 실패 {ticker}: {e}")
            time.sleep(1)
    _alert(f"[BUY RETRY] 시장가 전환 {ticker}")
    try:
        res = upbit.buy_market_order(ticker, total_krw)
        price = float(res.get("price", ask))
        qty = float(res.get("volume", total_krw / price))
    except Exception as e:  # pragma: no cover - final
        logger.error("[ORDER FAIL] fallback buy %s", e)
        _alert(f"[ORDER FAIL] 최종 매수 실패 {ticker}: {e}")
        return 0.0, 0.0
    logger.info("[BUY] fallback market %s %.6f %.6f", ticker, price, qty)
    return price, qty


def smart_sell(
    upbit: pyupbit.Upbit,
    ticker: str,
    quantity: float,
    slippage_limit: float = 0.0008,
    max_retry: int = 2,
    partial_ratio: float = 0.5,
    split_thresh: float = 1_000_000,
) -> Tuple[float, float]:
    """매도 모드(FORCE/PARTIAL/SPLIT)를 자동 결정해 주문한다."""
    ask, bid, spread = _fetch_spread(ticker)
    trade_value = bid * quantity
    if trade_value >= split_thresh:
        mode = "SPLIT"
    elif spread <= slippage_limit:
        mode = "PARTIAL"
    else:
        mode = "PARTIAL"

    if mode == "SPLIT":
        parts = max(2, min(3, int(trade_value // split_thresh) + 1))
        remain = quantity
        avg = 0.0
        sold = 0.0
        for i in range(parts):
            part = remain / (parts - i)
            res = upbit.sell_market_order(ticker, part)
            price = float(res.get("price", bid))
            qty = float(res.get("volume", part))
            uuid = res.get("uuid")
            if uuid and not is_filled(uuid):
                qty = check_filled_amount(uuid)
            avg = ((avg * sold) + price * qty) / (sold + qty)
            sold += qty
            remain -= qty
            logger.info("[SELL] split %s %.6f %.6f", ticker, price, qty)
            time.sleep(0.6)
        return avg, sold

    # PARTIAL 또는 기본
    m_qty = quantity * partial_ratio
    l_qty = quantity - m_qty
    res = upbit.sell_market_order(ticker, m_qty)
    m_price = float(res.get("price", bid))
    m_filled = float(res.get("volume", m_qty))
    uuid = res.get("uuid")
    if uuid and not is_filled(uuid):
        m_filled = check_filled_amount(uuid)

    for attempt in range(max_retry):
        tick = ask_tick(bid)
        limit_price = bid + tick
        res = upbit.sell_limit_order(ticker, limit_price, l_qty)
        uuid = res.get("uuid")
        time.sleep(0.5)
        if uuid and is_filled(uuid):
            l_filled = check_filled_amount(uuid)
            price = ((m_price * m_filled) + limit_price * l_filled) / (m_filled + l_filled)
            logger.info("[SELL] partial limit %s %.6f %.6f", ticker, limit_price, l_filled)
            return price, m_filled + l_filled
    res = upbit.sell_market_order(ticker, l_qty)
    price2 = float(res.get("price", bid))
    qty2 = float(res.get("volume", l_qty))
    uuid = res.get("uuid")
    if uuid and not is_filled(uuid):
        qty2 = check_filled_amount(uuid)
    avg = ((m_price * m_filled) + price2 * qty2) / (m_filled + qty2)
    logger.info("[SELL] partial fallback %s %.6f %.6f", ticker, price2, qty2)
    return avg, m_filled + qty2


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
