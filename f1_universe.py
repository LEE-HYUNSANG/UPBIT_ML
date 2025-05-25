"""Utility functions for selecting a trading universe.

The functions in this module retrieve market data from the Upbit REST API and
apply user defined filters in order to build the final monitoring universe. The
actual network calls will fail in environments without internet connectivity,
but the logic is implemented so that real data can be fetched once networking
is available.
"""

from __future__ import annotations

import json
import threading
import time
from typing import List, Dict

import requests

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
        }


def _fetch_json(url: str, params: Dict | None = None) -> list | dict:
    """Helper to perform a GET request and decode JSON."""
    response = requests.get(url, params=params, timeout=10)
    response.raise_for_status()
    return response.json()


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


def get_top_volume_tickers() -> List[str]:
    """Return a list of tickers with the highest 24h trading volume.

    The function queries all KRW markets from the Upbit API and sorts them by
    ``acc_trade_price_24h`` in descending order.
    """
    markets = _fetch_json(f"{BASE_URL}/market/all", {"isDetails": "true"})
    krw_markets = [m["market"] for m in markets if m["market"].startswith("KRW-")]

    # ``/ticker`` accepts up to 100 markets per request
    ticker_info = []
    for i in range(0, len(krw_markets), 100):
        chunk = krw_markets[i : i + 100]
        data = _fetch_json(f"{BASE_URL}/ticker", {"markets": ",".join(chunk)})
        ticker_info.extend(data)

    sorted_info = sorted(
        ticker_info, key=lambda x: x.get("acc_trade_price_24h", 0), reverse=True
    )

    return [item["market"] for item in sorted_info[:50]]


def apply_filters(tickers: List[str], config: Dict) -> List[str]:
    """Apply filter conditions to the given tickers.

    Parameters
    ----------
    tickers : list[str]
        List of ticker symbols.
    config : dict
        Dictionary with filter values such as price, volatility, tick
        and spread.

    Returns
    -------
    list[str]
        Filtered list of ticker symbols.
    """
    filtered: List[str] = []
    for i in range(0, len(tickers), 100):
        chunk = tickers[i : i + 100]
        ticker_data = _fetch_json(f"{BASE_URL}/ticker", {"markets": ",".join(chunk)})

        for item in ticker_data:
            price = item["trade_price"]
            if price < config.get("min_price", 0) or price > config.get("max_price", float("inf")):
                continue

            volatility = (item["high_price"] - item["low_price"]) / item["prev_closing_price"] * 100
            if volatility < config.get("min_volatility", 0):
                continue

            tick_range = (item["high_price"] - item["low_price"]) / _get_tick_size(price)
            if tick_range < config.get("min_ticks", 0):
                continue

            orderbook = _fetch_json(f"{BASE_URL}/orderbook", {"markets": item["market"]})[0]
            ask = orderbook["orderbook_units"][0]["ask_price"]
            bid = orderbook["orderbook_units"][0]["bid_price"]
            spread = (ask - bid) / price * 100
            if spread > config.get("max_spread", 100):
                continue

            filtered.append(item["market"])

    return filtered


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
    tickers = get_top_volume_tickers()
    volume_rank = int(cfg.get("volume_rank", 50))
    tickers = tickers[:volume_rank]
    filtered = apply_filters(tickers, cfg)
    # Return only the first five coins for monitoring
    return filtered[:5]


def update_universe(config: Dict | None = None) -> None:
    """Refresh the cached universe."""
    universe = select_universe(config)
    with _LOCK:
        _UNIVERSE.clear()
        _UNIVERSE.extend(universe)


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
                print("Universe update failed:", exc)
            time.sleep(interval)

    thread = threading.Thread(target=_loop, daemon=True)
    thread.start()
