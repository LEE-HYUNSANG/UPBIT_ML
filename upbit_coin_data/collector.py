"""Utility to fetch 1-minute OHLCV data from Upbit in parallel.

This script automatically filters KRW market coins based on price and then
collects 1 minute candles for the last 90 days. Requests are rate limited to
respect Upbit API policy (max 10 requests per second).
"""

from __future__ import annotations

import datetime
import os
import random
import threading
import time
from collections import deque
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List

import logging
from logging.handlers import RotatingFileHandler

import pandas as pd
import requests


BASE_URL = "https://api.upbit.com/v1"
DATA_DIR = "upbit_coin_data"
RATE_LIMIT = 10
PERIOD = 1.0

# Add tickers here to collect specific coins instead of automatic filtering.
# Example: SELECTED_MARKETS = ["KRW-BTC", "KRW-ETH"]
SELECTED_MARKETS: List[str] | None = None


def _setup_logging() -> None:
    os.makedirs(DATA_DIR, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [COLLECTOR] [%(levelname)s] %(message)s",
        handlers=[
            RotatingFileHandler(
                os.path.join(DATA_DIR, "collector.log"),
                maxBytes=5_000_000,
                backupCount=5,
                encoding="utf-8",
            ),
            logging.StreamHandler(),
        ],
    )


class RateLimiter:
    """Simple sliding window rate limiter."""

    def __init__(self, max_calls: int, period: float) -> None:
        self.max_calls = max_calls
        self.period = period
        self.calls: deque[float] = deque()
        self.lock = threading.Lock()

    def acquire(self) -> None:
        with self.lock:
            now = time.monotonic()
            while self.calls and now - self.calls[0] > self.period:
                self.calls.popleft()
            if len(self.calls) >= self.max_calls:
                sleep_for = self.period - (now - self.calls[0])
                if sleep_for > 0:
                    time.sleep(sleep_for)
            self.calls.append(time.monotonic())


_RATE_LIMITER = RateLimiter(RATE_LIMIT, PERIOD)


def _request(method: str, path: str, params: Dict | None = None) -> List | Dict:
    url = f"{BASE_URL}{path}"
    for _ in range(5):
        try:
            _RATE_LIMITER.acquire()
            resp = requests.request(method, url, params=params, timeout=10)
            if resp.status_code == 429 or resp.status_code >= 500:
                logging.warning(
                    "API error %s for %s - sleeping 10s", resp.status_code, path
                )
                time.sleep(10)
                continue
            resp.raise_for_status()
            return resp.json()
        except Exception as exc:  # pragma: no cover - network best effort
            logging.error("Request failed: %s", exc)
            time.sleep(10)
    return []


def get_krw_markets() -> List[str]:
    markets = _request("GET", "/market/all", {"isDetails": "false"})
    return [m["market"] for m in markets if str(m.get("market", "")).startswith("KRW-")]


def get_prices(markets: List[str]) -> Dict[str, float]:
    prices: Dict[str, float] = {}
    for i in range(0, len(markets), 100):
        chunk = markets[i : i + 100]
        data = _request("GET", "/ticker", {"markets": ",".join(chunk)})
        for item in data:
            prices[item.get("market", "")] = float(item.get("trade_price", 0))
    return prices


def filter_by_price(min_price: float = 500.0, max_price: float = 25000.0) -> List[str]:
    markets = get_krw_markets()
    prices = get_prices(markets)
    selected = [m for m, p in prices.items() if min_price <= p <= max_price]
    logging.info("Filtered %d markets within price range", len(selected))
    return selected


def _fetch_candles(market: str, to: datetime.datetime | None) -> List[dict]:
    params = {"market": market, "count": 200}
    if to:
        params["to"] = to.strftime("%Y-%m-%d %H:%M:%S")
    return _request("GET", "/candles/minutes/1", params)


def collect_market(market: str) -> None:
    end = datetime.datetime.utcnow()
    start_limit = end - datetime.timedelta(days=90)
    all_rows: List[pd.DataFrame] = []

    to_ts = end
    while True:
        rows = _fetch_candles(market, to_ts)
        if not rows:
            break
        df = pd.DataFrame(rows)
        all_rows.append(df)
        oldest = pd.to_datetime(df["candle_date_time_utc"].iloc[-1])
        if oldest <= start_limit:
            break
        to_ts = oldest - datetime.timedelta(minutes=1)
        time.sleep(random.uniform(1, 2))

    if not all_rows:
        logging.warning("No data for %s", market)
        return

    data = pd.concat(all_rows, ignore_index=True)
    data.drop_duplicates(subset="candle_date_time_utc", inplace=True)
    data.sort_values("candle_date_time_utc", ascending=True, inplace=True)
    data.reset_index(drop=True, inplace=True)

    oldest = pd.to_datetime(data["candle_date_time_utc"].iloc[0]).strftime("%Y%m%d_%H%M%S")
    newest = pd.to_datetime(data["candle_date_time_utc"].iloc[-1]).strftime("%Y%m%d_%H%M%S")
    fname = f"{market}_{oldest}-{newest}.csv"
    path = os.path.join(DATA_DIR, fname)
    data.to_csv(path, index=False)
    logging.info("Saved %s (%d rows)", path, len(data))


def run() -> None:
    _setup_logging()
    if SELECTED_MARKETS:
        markets = list(SELECTED_MARKETS)
        logging.info("Collecting data for %d user-specified markets", len(markets))
    else:
        markets = filter_by_price()
        logging.info("Collecting data for %d markets", len(markets))
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = {executor.submit(collect_market, m): m for m in markets}
        for fut in as_completed(futures):
            m = futures[fut]
            try:
                fut.result()
            except Exception as exc:  # pragma: no cover - best effort
                logging.error("Error collecting %s: %s", m, exc)


if __name__ == "__main__":
    run()
