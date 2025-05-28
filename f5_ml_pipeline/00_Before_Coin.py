import os
import time
import requests
from datetime import datetime, timedelta
from typing import List, Dict
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

from utils import ensure_dir
import pandas as pd
from tqdm import tqdm


LOG_PATH = Path("logs/before_coin.log")


def setup_logger() -> logging.Logger:
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
    return logging.getLogger(__name__)


logger = setup_logger()

# Configuration
BASE_URL = "https://api.upbit.com"
DATA_DIR = os.path.join(os.path.dirname(__file__), "ml_data", "00_back_raw")
REQUEST_DELAY = 0.15  # seconds between API calls
MIN_PRICE = 500
MAX_PRICE = 25000
MIN_ACC_TRADE_PRICE_24H = 1_400_000_000  # 14억 KRW

os.makedirs(DATA_DIR, exist_ok=True)


def _request_json(url: str, params: Dict[str, str] | None = None) -> List[Dict]:
    while True:
        try:
            response = requests.get(url, params=params, timeout=10)
            if response.status_code == 429:
                logger.info("Rate limit hit. Sleeping...")
                time.sleep(1)
                continue
            response.raise_for_status()
            return response.json()
        except requests.RequestException as exc:
            logger.info(f"Request error: {exc}. Retrying...")
            time.sleep(1)


def get_krw_markets() -> List[str]:
    url = f"{BASE_URL}/v1/market/all"
    data = _request_json(url, params={"isDetails": "false"})
    markets = [m["market"] for m in data if m["market"].startswith("KRW-")]
    logger.info(f"Fetched {len(markets)} KRW markets")
    return markets


def get_market_tickers(markets: List[str]) -> List[Dict]:
    """Return ticker info (가격, 거래대금 포함) for given markets."""
    url = f"{BASE_URL}/v1/ticker"
    tickers: List[Dict] = []
    for i in range(0, len(markets), 100):
        chunk = markets[i : i + 100]
        params = {"markets": ",".join(chunk)}
        data = _request_json(url, params=params)
        tickers.extend(data)
        time.sleep(REQUEST_DELAY)
    return tickers


def fetch_minutes(market: str, start_dt: datetime, end_dt: datetime) -> List[Dict]:
    url = f"{BASE_URL}/v1/candles/minutes/1"
    all_rows: List[Dict] = []
    to_dt = end_dt
    total_minutes = int((end_dt - start_dt).total_seconds() // 60)
    with tqdm(total=total_minutes, desc=f"{market}_1min") as bar:
        while to_dt > start_dt:
            params = {
                "market": market,
                "to": to_dt.strftime("%Y-%m-%d %H:%M:%S"),
                "count": 200,
            }
            rows = _request_json(url, params=params)
            if not rows:
                break
            all_rows.extend(rows)
            oldest = rows[-1]["candle_date_time_utc"]
            to_dt = datetime.strptime(oldest, "%Y-%m-%dT%H:%M:%S") - timedelta(minutes=1)
            bar.update(len(rows))
            time.sleep(REQUEST_DELAY)
    return all_rows


def fetch_orderbook(market: str) -> List[Dict]:
    url = f"{BASE_URL}/v1/orderbook"
    data = _request_json(url, params={"markets": market})
    return data if isinstance(data, list) else [data]


def fetch_trades(market: str, count: int = 100) -> List[Dict]:
    url = f"{BASE_URL}/v1/trades/ticks"
    data = _request_json(url, params={"market": market, "count": count})
    return data if isinstance(data, list) else [data]


def fetch_ticker(market: str) -> List[Dict]:
    url = f"{BASE_URL}/v1/ticker"
    data = _request_json(url, params={"markets": market})
    return data if isinstance(data, list) else [data]


def save_csv(market: str, rows: List[Dict], label: str = ""):
    if not rows:
        logger.info(f"No data for {market} {label}")
        return
    df = pd.DataFrame(rows)
    time_col = next(
        (
            col
            for col in [
                "timestamp",
                "candle_date_time_utc",
                "trade_time_utc",
                "created_at",
            ]
            if col in df.columns
        ),
        None,
    )
    if time_col:
        df.sort_values(time_col, inplace=True)
        start_str = pd.to_datetime(df[time_col].iloc[0]).strftime("%Y%m%d_%H%M%S")
        end_str = pd.to_datetime(df[time_col].iloc[-1]).strftime("%Y%m%d_%H%M%S")
    else:
        now = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        start_str = end_str = now
    filename = f"{market}_{label}_{start_str}-{end_str}.csv" if label else f"{market}_{start_str}-{end_str}.csv"
    path = os.path.join(DATA_DIR, filename)
    df.to_csv(path, index=False)
    logger.info(f"Saved {market} {label} data to {path}")


def main():
    end_dt = datetime.utcnow().replace(second=0, microsecond=0)
    start_dt = end_dt - timedelta(days=90)

    markets = get_krw_markets()
    tickers = get_market_tickers(markets)

    # 조건: 가격 500~25000원 & 24H 거래대금 14억 이상
    targets = [
        t["market"]
        for t in tickers
        if (
            MIN_PRICE <= t.get("trade_price", 0) <= MAX_PRICE
            and t.get("acc_trade_price_24h", 0) >= MIN_ACC_TRADE_PRICE_24H
        )
    ]
    logger.info(f"Target coins ({len(targets)}): {targets}")

    for market in targets:
        # 1분반표(캐듄)
        rows_min = fetch_minutes(market, start_dt, end_dt)
        save_csv(market, rows_min, label="1min")

        # 가장 최근 호가(Orderbook)
        try:
            rows_orderbook = fetch_orderbook(market)
            save_csv(market, rows_orderbook, label="orderbook")
        except Exception as e:
            logger.info(f"Orderbook fetch error for {market}: {e}")

        # 최근 체결내용(Trades/Tick)
        try:
            rows_trades = fetch_trades(market, count=100)
            save_csv(market, rows_trades, label="trades")
        except Exception as e:
            logger.info(f"Trades fetch error for {market}: {e}")

        # 실시간 시세(Ticker)
        try:
            rows_ticker = fetch_ticker(market)
            save_csv(market, rows_ticker, label="ticker")
        except Exception as e:
            logger.info(f"Ticker fetch error for {market}: {e}")

    logger.info("DONE")


if __name__ == "__main__":
    main()
