import os
import time
import requests
from datetime import datetime, timedelta
from typing import List, Dict

import pandas as pd
from tqdm import tqdm

# Configuration
BASE_URL = "https://api.upbit.com"
DATA_DIR = os.path.join(os.path.dirname(__file__), "ml_data", "01_raw")
REQUEST_DELAY = 0.15  # seconds between API calls
os.makedirs(DATA_DIR, exist_ok=True)


def _request_json(url: str, params: Dict[str, str] | None = None) -> List[Dict]:
    """Perform GET request with retry and rate limit handling."""
    while True:
        try:
            response = requests.get(url, params=params, timeout=10)
            if response.status_code == 429:
                print("Rate limit hit. Sleeping...")
                time.sleep(1)
                continue
            response.raise_for_status()
            return response.json()
        except requests.RequestException as exc:
            print(f"Request error: {exc}. Retrying...")
            time.sleep(1)


def get_krw_markets() -> List[str]:
    """Return list of KRW markets."""
    url = f"{BASE_URL}/v1/market/all"
    data = _request_json(url, params={"isDetails": "false"})
    markets = [m["market"] for m in data if m["market"].startswith("KRW-")]
    print(f"Fetched {len(markets)} KRW markets")
    return markets


def get_current_prices(markets: List[str]) -> Dict[str, float]:
    """Fetch current price for markets."""
    prices: Dict[str, float] = {}
    url = f"{BASE_URL}/v1/ticker"
    for i in range(0, len(markets), 100):
        chunk = markets[i : i + 100]
        params = {"markets": ",".join(chunk)}
        data = _request_json(url, params=params)
        for item in data:
            prices[item["market"]] = item["trade_price"]
        time.sleep(REQUEST_DELAY)
    return prices


def fetch_minutes(market: str, start_dt: datetime, end_dt: datetime) -> List[Dict]:
    """Fetch 1 minute candles between start_dt and end_dt."""
    url = f"{BASE_URL}/v1/candles/minutes/1"
    all_rows: List[Dict] = []
    to_dt = end_dt
    total_minutes = int((end_dt - start_dt).total_seconds() // 60)
    with tqdm(total=total_minutes, desc=market) as bar:
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


def save_csv(market: str, rows: List[Dict]):
    """Save rows to CSV in DATA_DIR."""
    if not rows:
        print(f"No data for {market}")
        return
    df = pd.DataFrame(rows)
    df.sort_values("timestamp", inplace=True)
    start_str = pd.to_datetime(df["candle_date_time_utc"].iloc[0]).strftime("%Y%m%d_%H%M%S")
    end_str = pd.to_datetime(df["candle_date_time_utc"].iloc[-1]).strftime("%Y%m%d_%H%M%S")
    filename = f"{market}_{start_str}-{end_str}.csv"
    path = os.path.join(DATA_DIR, filename)
    df.to_csv(path, index=False)
    print(f"Saved {market} data to {path}")


def main():
    end_dt = datetime.utcnow().replace(second=0, microsecond=0)
    start_dt = end_dt - timedelta(days=90)

    markets = get_krw_markets()
    prices = get_current_prices(markets)
    targets = [m for m in markets if 500 <= prices.get(m, 0) <= 25000]
    print(f"Collecting data for {len(targets)} markets")

    for market in targets:
        rows = fetch_minutes(market, start_dt, end_dt)
        save_csv(market, rows)

    print("DONE")


if __name__ == "__main__":
    main()
