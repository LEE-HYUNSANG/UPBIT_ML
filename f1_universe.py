"""Utility functions for selecting a trading universe.

The functions in this module retrieve market data from the Upbit REST API and
apply user defined filters in order to build the final monitoring universe. The
actual network calls will fail in environments without internet connectivity,
but the logic is implemented so that real data can be fetched once networking
is available.
"""

from __future__ import annotations

import json
import os
import threading
import time
from typing import Dict, List

import logging
import requests

os.makedirs("logs", exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [F1] [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("logs/F1_signal_engine.log", encoding="utf-8"),
        logging.StreamHandler(),
    ],
)

BASE_URL = "https://api.upbit.com/v1"
CONFIG_PATH = "config/universe.json"

_UNIVERSE: List[str] = []
_LOCK = threading.Lock()


def load_config(path: str = CONFIG_PATH) -> Dict:
    """Load universe filter configuration.

    Parameters
    ----------
    path : str
        Path to a JSON configuration file.

    Returns
    -------
    dict
        Dictionary with configuration values.  Reasonable defaults are returned
        when the file does not exist.
    """
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        # Default values roughly matching the modal window in the template.
        return {
            "min_price": 0,
            "max_price": float("inf"),
            "min_volatility": 0.0,
            "min_ticks": 0,
            "max_spread": 100.0,
            "volume_rank": 50,
            "universe_size": 5,
        }


def _fetch_json(url: str, params: Dict | None = None) -> list | dict:
    """Helper to perform a GET request and decode JSON."""
    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        return response.json()
    except Exception as exc:  # pragma: no cover - network best effort
        logging.error(f"[F1][API] Request failed: {url} | params={params} | {exc}")
        return []


def _get_tick_size(price: float) -> float:
    """Return the tick size for a given price according to Upbit rules."""
    if price < 10:
        return 0.01
    if price < 100:
        return 0.1
    if price < 1000:
        return 1
    if price < 10000:
        return 5
    if price < 100000:
        return 10
    if price < 500000:
        return 50
    if price < 1000000:
        return 100
    return 500


def get_top_volume_tickers(size: int = 50) -> List[str]:
    """Return a list of tickers with the highest 24h trading volume."""

    markets = _fetch_json(f"{BASE_URL}/market/all", {"isDetails": "true"})
    if not markets:
        logging.warning("[F1][SCAN] 거래대금 TOP 리스트를 불러오지 못했습니다!")
        return []

    krw_markets = [
        m["market"] for m in markets if m.get("market", "").startswith("KRW-")
    ]

    ticker_info = []
    for i in range(0, len(krw_markets), 100):
        chunk = krw_markets[i : i + 100]
        data = _fetch_json(f"{BASE_URL}/ticker", {"markets": ",".join(chunk)})
        ticker_info.extend(data)

    sorted_info = sorted(
        ticker_info, key=lambda x: x.get("acc_trade_price_24h", 0), reverse=True
    )

    tickers = [item["market"] for item in sorted_info[:size]]
    logging.info(f"거래대금 TOP {size} 종목: {tickers}")
    return tickers


def apply_filters(tickers: List[str], config: Dict) -> List[str]:
    """Apply filter conditions to the given tickers and log each step."""

    info: List[Dict] = []
    for i in range(0, len(tickers), 100):
        chunk = tickers[i : i + 100]
        ticker_data = _fetch_json(f"{BASE_URL}/ticker", {"markets": ",".join(chunk)})

        for item in ticker_data:
            price = item.get("trade_price", 0)
            volatility = (
                (item.get("high_price", 0) - item.get("low_price", 0))
                / item.get("prev_closing_price", 1)
                * 100
            )
            tick_range = (
                item.get("high_price", 0) - item.get("low_price", 0)
            ) / _get_tick_size(price)
            orderbook = _fetch_json(
                f"{BASE_URL}/orderbook", {"markets": item.get("market")}
            )
            if orderbook:
                ask = orderbook[0]["orderbook_units"][0]["ask_price"]
                bid = orderbook[0]["orderbook_units"][0]["bid_price"]
            else:
                ask = bid = price
            spread = (ask - bid) / price * 100 if price else 0

            info.append(
                {
                    "symbol": item.get("market", ""),
                    "price": price,
                    "volatility": volatility,
                    "tick_range": tick_range,
                    "spread": spread,
                }
            )

    min_price = config.get("min_price", 0)
    max_price = config.get("max_price", float("inf"))
    min_ticks = config.get("min_ticks", 0)
    price_filtered = [
        t
        for t in info
        if min_price <= t["price"] <= max_price and t["tick_range"] >= min_ticks
    ]
    logging.info(
        f"가격 필터 통과: {[t['symbol'] for t in price_filtered]} | 가격 {min_price}-{max_price} | min_ticks={min_ticks}"
    )

    min_vol = config.get("min_volatility", 0)
    volatility_filtered = [t for t in price_filtered if t["volatility"] >= min_vol]
    logging.info(
        f"변동성(ATR) 필터 통과: {[t['symbol'] for t in volatility_filtered]} | min_volatility={min_vol}"
    )

    max_spread = config.get("max_spread", 100)
    spread_filtered = [t for t in volatility_filtered if t["spread"] <= max_spread]
    logging.info(
        f"스프레드 필터 통과: {[t['symbol'] for t in spread_filtered]} | max_spread={max_spread}"
    )

    return [t["symbol"] for t in spread_filtered]


def select_universe(config: Dict | None = None) -> List[str]:
    """Select the final universe of tradable tickers.

    Parameters
    ----------
    config : dict, optional
        Filter configuration that will be passed to :func:`apply_filters`.

    Returns
    -------
    list[str]
        Final list of ticker symbols.
    """
    cfg = config or load_config()
    volume_rank = int(cfg.get("volume_rank", 50))
    tickers = get_top_volume_tickers(volume_rank)
    filtered = apply_filters(tickers, cfg)

    universe_size = int(cfg.get("universe_size", 0))
    universe = filtered if universe_size <= 0 else filtered[:universe_size]
    if not universe:
        logging.error("최종 Universe가 비었습니다. 필터 조건/데이터 확인 필요!")
    logging.info(f"최종 Universe 선정: {universe}")
    return universe


def update_universe(config: Dict | None = None) -> None:
    """Refresh the cached universe."""
    universe = select_universe(config)
    with _LOCK:
        _UNIVERSE.clear()
        _UNIVERSE.extend(universe)
    logging.info(f"Universe updated: {universe}")


def get_universe() -> List[str]:
    """Return the last cached universe."""
    with _LOCK:
        return list(_UNIVERSE)


def schedule_universe_updates(interval: int = 1800, config: Dict | None = None) -> None:
    """Start a background thread refreshing the universe periodically."""

    def _loop() -> None:
        while True:
            try:
                update_universe(config)
            except Exception as exc:  # pragma: no cover - best effort
                logging.error(f"Universe update failed: {exc}")
            time.sleep(interval)

    thread = threading.Thread(target=_loop, daemon=True)
    thread.start()
