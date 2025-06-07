"""Download last 100k minutes of 1 minute OHLCV data."""

from __future__ import annotations

import json
import logging
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List
import tempfile

import pandas as pd
import requests

from utils import ensure_dir, file_lock, save_parquet_atomic, backup_file, setup_logger

BASE_URL = "https://api.upbit.com"
PIPELINE_ROOT = Path(__file__).resolve().parent
DATA_ROOT = PIPELINE_ROOT / "ml_data" / "99_100day_1min_data"
ROOT_DIR = PIPELINE_ROOT.parent
COIN_LIST_FILE = ROOT_DIR / "config" / "f1_f5_data_collection_list.json"
REQUEST_DELAY = 0.2
LOG_PATH = ROOT_DIR / "logs" / "f5" / "99_100day_1min_data.log"
CANDLE_LIMIT = 100_000


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


def get_ohlcv_history(market: str) -> pd.DataFrame:
    """Fetch last 100k minutes of minute candles for ``market``."""
    url = f"{BASE_URL}/v1/candles/minutes/1"
    end = datetime.utcnow().replace(second=0, microsecond=0)
    remaining = CANDLE_LIMIT
    to = end.isoformat()
    frames: List[pd.DataFrame] = []

    while remaining > 0:
        count = min(200, remaining)
        params = {"market": market, "count": count, "to": to}
        data = _request_json(url, params)
        if not data:
            break
        frames.append(pd.DataFrame(data))
        remaining -= len(data)
        to = data[-1]["candle_date_time_utc"]
        time.sleep(REQUEST_DELAY)

    if not frames:
        return pd.DataFrame()
    df = pd.concat(frames, ignore_index=True)
    df = df.sort_values("candle_date_time_utc").reset_index(drop=True)
    return df


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
    """Save ``df`` under ``root`` directory."""
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


def validate_data(root: Path, markets: Iterable[str]) -> List[str]:
    """Return list of markets with incomplete data."""
    incomplete: List[str] = []
    for market in markets:
        file_path = root / f"{market}_rawdata.parquet"
        try:
            df = pd.read_parquet(file_path)
            if len(df) < CANDLE_LIMIT:
                logging.warning(
                    "%s expected %d rows but got %d",
                    market,
                    CANDLE_LIMIT,
                    len(df),
                )
                incomplete.append(market)
        except Exception as exc:
            logging.error("Failed reading %s: %s", file_path.name, exc)
            incomplete.append(market)
    return incomplete


def ask_retry(market: str, rows: int) -> bool:
    """Return ``True`` to retry collection of ``market``."""
    while True:
        ans = input(
            f"{market} has {rows} rows (expected {CANDLE_LIMIT}). Retry [y/n]? "
        ).strip().lower()
        if ans in {"y", "n"}:
            return ans == "y"


def collect_markets(markets: Iterable[str]) -> List[str]:
    """Collect history for ``markets`` with progress output."""
    items = list(markets)
    total = len(items)
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_root = Path(tmpdir)
        collected: List[str] = []
        incomplete: List[str] = []
        for idx, market in enumerate(items, start=1):
            print(f"[{idx}/{total}] Collecting {market} ...", flush=True)
            try:
                df = get_ohlcv_history(market)
                if df.empty:
                    logging.warning("No data for %s", market)
                    incomplete.append(market)
                    continue
                if len(df) < CANDLE_LIMIT:
                    logging.warning(
                        "%s expected %d rows but got %d",
                        market,
                        CANDLE_LIMIT,
                        len(df),
                    )
                    incomplete.append(market)
                    continue
                save_data(df, market, root=tmp_root)
                collected.append(market)
                print(f"[{idx}/{total}] {market} done", flush=True)
            except Exception as exc:  # pragma: no cover - best effort
                logging.error("Collect error %s: %s", market, exc)
                incomplete.append(market)

        for market in collected:
            file = tmp_root / f"{market}_rawdata.parquet"
            try:
                df = pd.read_parquet(file)
                save_data(df, market, root=DATA_ROOT)
            except Exception as exc:  # pragma: no cover - best effort
                logging.error("Finalize error %s: %s", file.name, exc)
        return incomplete


def main() -> None:
    """Download the last 100k minutes of minute data."""
    setup_logger(LOG_PATH)
    markets = load_coin_list()
    if not markets:
        logging.error("No markets to collect")
        return

    ensure_dir(DATA_ROOT)
    for old in DATA_ROOT.glob("*"):
        if old.is_file():
            old.unlink(missing_ok=True)

    pending = markets
    while pending:
        logging.info("Collect 100k history for %s", pending)
        incomplete = collect_markets(pending)
        incomplete.extend(validate_data(DATA_ROOT, pending))
        next_round: List[str] = []
        for market in set(incomplete):
            file_path = DATA_ROOT / f"{market}_rawdata.parquet"
            try:
                rows = len(pd.read_parquet(file_path))
            except Exception:
                rows = 0
            retry = ask_retry(market, rows)
            file_path.unlink(missing_ok=True)
            if retry:
                next_round.append(market)
            else:
                logging.info("User aborted collection for %s", market)
                return
        pending = next_round
        if pending:
            logging.info("Retrying incomplete markets: %s", pending)


if __name__ == "__main__":
    main()
