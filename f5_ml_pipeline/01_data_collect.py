"""Real-time Upbit data collector.

이 스크립트는 ``coin_list_data_collection.json``에 지정된 코인에 대해 매 1분
단위로 OHLCV, 호가, 체결, 시세 데이터를 수집합니다. 수집된 데이터는
``ml_data/realtime/<type>/`` 폴더 아래에 코인별 Parquet 파일로 저장됩니다.
"""

from __future__ import annotations

import json
import logging
import time
from datetime import datetime, timedelta
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Dict, Iterable, List

import pandas as pd
import requests

from utils import ensure_dir

BASE_URL = "https://api.upbit.com"
DATA_ROOT = Path("ml_data/realtime")

# Use absolute path so the script works regardless of the current
# working directory.
ROOT_DIR = Path(__file__).resolve().parent.parent
COIN_LIST_FILE = ROOT_DIR / "config" / "coin_list_data_collection.json"
REQUEST_DELAY = 0.2  # seconds between API calls
LOG_PATH = Path("logs/data_collect.log")


def setup_logger() -> None:
    """Configure rotating file logger."""
    ensure_dir(LOG_PATH.parent)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            RotatingFileHandler(
                LOG_PATH,
                encoding="utf-8",
                maxBytes=50_000 * 1024,
                backupCount=5,
            ),
            logging.StreamHandler(),
        ],
        force=True,
    )


def load_coin_list(path: str = COIN_LIST_FILE) -> List[str]:
    """Return list of markets to collect."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):
            return [str(x) for x in data]
    except FileNotFoundError:
        logging.error("Coin list file not found: %s", path)
    except Exception as exc:  # pragma: no cover - best effort
        logging.error("Coin list load error: %s", exc)
    return []


def _request_json(url: str, params: Dict | None = None, retries: int = 3) -> List[Dict]:
    """Wrapper for ``requests.get`` with retry and rate limiting."""
    for _ in range(retries):
        try:
            resp = requests.get(url, params=params, timeout=10)
            if resp.status_code == 429:
                time.sleep(1)
                continue
            resp.raise_for_status()
            return resp.json()
        except Exception as exc:  # pragma: no cover - network error path
            logging.warning("Request error %s: %s", url, exc)
            time.sleep(1)
    return []


def get_ohlcv(market: str) -> List[Dict]:
    """Fetch latest 1 minute OHLCV."""
    url = f"{BASE_URL}/v1/candles/minutes/1"
    return _request_json(url, params={"market": market, "count": 1})


def get_orderbook(market: str) -> List[Dict]:
    """Fetch current orderbook."""
    url = f"{BASE_URL}/v1/orderbook"
    return _request_json(url, params={"markets": market})


def get_trades(market: str) -> List[Dict]:
    """Fetch latest trades."""
    url = f"{BASE_URL}/v1/trades/ticks"
    return _request_json(url, params={"market": market, "count": 50})


def get_ticker(market: str) -> List[Dict]:
    """Fetch current ticker info."""
    url = f"{BASE_URL}/v1/ticker"
    return _request_json(url, params={"markets": market})


def _dedupe_columns(df: pd.DataFrame) -> List[str] | None:
    """Return best column set for duplicate removal."""
    candidates = [
        ["timestamp", "market"],
        ["trade_timestamp", "market"],
        ["sequential_id"],
        ["candle_date_time_utc", "market"],
    ]
    for cols in candidates:
        if all(c in df.columns for c in cols):
            return cols
    return None


def save_data(df: pd.DataFrame, data_type: str, market: str, ts: datetime) -> None:
    """Append ``df`` to Parquet file under ``data_type`` directory."""
    date_str = ts.strftime("%Y%m%d")
    dir_path = ensure_dir(DATA_ROOT / data_type)
    file_path = dir_path / f"{market}_{date_str}.parquet"

    if file_path.exists():
        try:
            old = pd.read_parquet(file_path)
            df = pd.concat([old, df], ignore_index=True)
        except Exception as exc:  # pragma: no cover - best effort
            logging.warning("Failed reading %s: %s", file_path.name, exc)

    subset = _dedupe_columns(df)
    if subset:
        before = len(df)
        df = df.drop_duplicates(subset=subset)
        removed = before - len(df)
        if removed:
            logging.info("Drop duplicates %s - %d rows", file_path.name, removed)

    try:
        df.to_parquet(file_path, index=False)
    except Exception as exc:  # pragma: no cover - best effort
        logging.error("Parquet save failed %s: %s", file_path.name, exc)


def collect_once(markets: Iterable[str]) -> None:
    """Collect data for all markets a single time."""
    ts = datetime.utcnow()
    for market in markets:
        try:
            ohlcv = get_ohlcv(market)
            if ohlcv:
                save_data(pd.DataFrame(ohlcv), "ohlcv", market, ts)
            time.sleep(REQUEST_DELAY)

            orderbook = get_orderbook(market)
            if orderbook:
                save_data(pd.DataFrame(orderbook), "orderbook", market, ts)
            time.sleep(REQUEST_DELAY)

            trades = get_trades(market)
            if trades:
                save_data(pd.DataFrame(trades), "trades", market, ts)
            time.sleep(REQUEST_DELAY)

            ticker = get_ticker(market)
            if ticker:
                save_data(pd.DataFrame(ticker), "ticker", market, ts)
            time.sleep(REQUEST_DELAY)
        except Exception as exc:  # pragma: no cover - best effort
            logging.error("Collect error %s: %s", market, exc)


def next_minute(now: datetime | None = None) -> datetime:
    """Return datetime of the next minute boundary."""
    now = now or datetime.utcnow()
    return (now.replace(second=0, microsecond=0) + timedelta(minutes=1))


def main() -> None:
    """Run the continuous data collector."""
    ensure_dir(DATA_ROOT)
    setup_logger()
    markets = load_coin_list()
    if not markets:
        logging.error("No markets to collect")
        return

    logging.info("Start data collection for %s", markets)

    while True:
        start = datetime.utcnow()
        collect_once(markets)
        sleep_until = next_minute(start)
        remaining = (sleep_until - datetime.utcnow()).total_seconds()
        if remaining > 0:
            time.sleep(remaining)


if __name__ == "__main__":
    main()

