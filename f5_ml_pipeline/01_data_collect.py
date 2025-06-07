"""Real-time Upbit data collector.

이 스크립트는 ``f1_f5_data_collection_list.json``에 지정된 코인에 대해 매 1분
단위로 **OHLCV** 데이터만 수집합니다. 최신 분봉은
``ml_data/00_now_1min_data/`` 폴더에 저장되고 기존 Raw 데이터와 병합하여
``ml_data/01_raw/``에 갱신합니다.
"""

from __future__ import annotations

import json
import logging
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Iterable, List

import pandas as pd
import requests

from utils import ensure_dir, file_lock, save_parquet_atomic, backup_file, setup_logger

BASE_URL = "https://api.upbit.com"
# Base directory of this pipeline
PIPELINE_ROOT = Path(__file__).resolve().parent
# Store output under the pipeline data directory regardless of CWD
DATA_ROOT = PIPELINE_ROOT / "ml_data" / "01_raw"
NOW_DATA_ROOT = PIPELINE_ROOT / "ml_data" / "00_now_1min_data"

# Use absolute path so the script works regardless of the current
# working directory.
ROOT_DIR = PIPELINE_ROOT.parent
COIN_LIST_FILE = ROOT_DIR / "config" / "f1_f5_data_collection_list.json"
REQUEST_DELAY = 0.2  # seconds between API calls
LOG_PATH = ROOT_DIR / "logs" / "f5" / "F5_data_collect.log"
START_DELAY = 5  # seconds after each one-minute candle closes


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


def get_ohlcv_range(market: str, count: int = 60) -> List[Dict]:
    """Fetch ``count`` latest 1 minute OHLCV rows."""
    url = f"{BASE_URL}/v1/candles/minutes/1"
    return _request_json(url, params={"market": market, "count": count})


# Only OHLCV is collected. The helper functions for orderbook, trades and ticker
# have been removed to keep the collector focused on minute candles.


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


def save_data(df: pd.DataFrame, market: str, root: Path = DATA_ROOT) -> None:
    """Append ``df`` to ``root`` directory."""
    dir_path = ensure_dir(root)
    file_path = dir_path / f"{market}_rawdata.parquet"

    lock_file = file_path.with_suffix(file_path.suffix + ".lock")
    with file_lock(lock_file):
        if file_path.exists():
            try:
                old = pd.read_parquet(file_path)
                df = pd.concat([old, df], ignore_index=True)
            except Exception as exc:  # pragma: no cover - best effort
                logging.warning("Failed reading %s: %s", file_path.name, exc)
                new = backup_file(file_path)
                logging.info("Backed up corrupt file to %s", new.name)

        subset = _dedupe_columns(df)
        if subset:
            before = len(df)
            df = df.drop_duplicates(subset=subset)
            removed = before - len(df)
            if removed:
                logging.info("Drop duplicates %s - %d rows", file_path.name, removed)

        try:
            save_parquet_atomic(df, file_path)
        except Exception as exc:  # pragma: no cover - best effort
            logging.error("Parquet save failed %s: %s", file_path.name, exc)


def fill_last_hour(market: str) -> None:
    """Ensure last hour of minute data is complete for ``market``."""
    file_path = DATA_ROOT / f"{market}_rawdata.parquet"
    if not file_path.exists():
        return
    try:
        df = pd.read_parquet(file_path)
    except Exception as exc:
        logging.error("Failed reading %s: %s", file_path.name, exc)
        return

    if "candle_date_time_utc" not in df.columns:
        return

    ts = pd.to_datetime(df["candle_date_time_utc"], utc=True)
    end = datetime.utcnow().replace(second=0, microsecond=0)
    start = end - timedelta(hours=1)
    recent_ts = ts[ts >= start]
    idx = pd.date_range(start=start, end=end, freq="1min")
    missing = idx.difference(recent_ts)
    if missing.empty:
        return
    logging.info("%s missing %d rows - fetching", market, len(missing))
    new_rows = get_ohlcv_range(market, count=60)
    if new_rows:
        save_data(pd.DataFrame(new_rows), market)


def collect_once(markets: Iterable[str]) -> None:
    """Collect data for all markets a single time."""
    for market in markets:
        try:
            ohlcv = get_ohlcv(market)
            if ohlcv:
                df_now = pd.DataFrame(ohlcv)
                save_data(df_now, market, root=NOW_DATA_ROOT)
                save_data(df_now, market)
                fill_last_hour(market)
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
    ensure_dir(NOW_DATA_ROOT)
    setup_logger(LOG_PATH)
    markets = load_coin_list()
    if not markets:
        logging.error("No markets to collect")
        return

    logging.info("Start data collection for %s", markets)

    # Wait until 5 seconds after the current one-minute candle closes
    first_start = next_minute() + timedelta(seconds=START_DELAY)
    wait = (first_start - datetime.utcnow()).total_seconds()
    if wait > 0:
        time.sleep(wait)

    while True:
        start = datetime.utcnow()
        collect_once(markets)
        sleep_until = next_minute(start) + timedelta(seconds=START_DELAY)
        remaining = (sleep_until - datetime.utcnow()).total_seconds()
        if remaining > 0:
            time.sleep(remaining)


if __name__ == "__main__":
    main()

