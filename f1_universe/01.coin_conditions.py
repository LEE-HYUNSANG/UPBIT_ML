"""Generate a coin list for ML data collection using simple filters."""

from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from typing import Dict, List

try:
    import requests
except Exception:  # pragma: no cover - fallback when requests missing
    requests = None
    import urllib.request as _urlreq
    from urllib.parse import urlencode

# === Coin Conditions ===
PRICE1_MIN = 700
PRICE1_MAX = 26666
PRICE2_MIN = 0
PRICE2_MAX = 0
TRADE_VALUE_MIN = 1400000000

# PRICE2_MIN = 0 and PRICE2_MAX = 0 disables the second range

BASE_URL = "https://api.upbit.com"
ROOT_DIR = Path(__file__).resolve().parents[1]
COIN_LIST_FILE = ROOT_DIR / "config" / "f1_f5_data_collection_list.json"
LOG_FILE = ROOT_DIR / "logs" / "f1" / "coin_conditions.log"
LOG_FILE.parent.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [F1] [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(),
    ],
)


def _request_json(url: str, params: Dict | None = None, retries: int = 3) -> List[Dict]:
    """Return JSON from ``url`` with simple retry logic.

    Parameters
    ----------
    url : str
        Endpoint to request.
    params : dict, optional
        Query parameters passed to the request.
    retries : int, optional
        Number of attempts before giving up.

    Returns
    -------
    list[dict]
        Parsed JSON data or an empty list when the request fails.
    """
    for _ in range(retries):
        try:
            if requests:
                resp = requests.get(url, params=params, timeout=10)
                if resp.status_code == 429:
                    time.sleep(1)
                    continue
                resp.raise_for_status()
                return resp.json()
            else:  # pragma: no cover - fallback path
                if params:
                    url = f"{url}?{urlencode(params)}"
                with _urlreq.urlopen(url, timeout=10) as r:
                    import json as _json
                    return _json.loads(r.read().decode())
        except Exception as exc:  # pragma: no cover - network best effort
            logging.warning("Request error %s: %s", url, exc)
            time.sleep(1)
    return []


def fetch_markets() -> List[str]:
    """Return a list of all KRW market codes from Upbit."""
    url = f"{BASE_URL}/v1/market/all"
    data = _request_json(url)
    return [d["market"] for d in data if str(d.get("market", "")).startswith("KRW-")]


def fetch_candles(market: str) -> List[Dict]:
    """Fetch the last six one-minute candles for ``market``."""
    url = f"{BASE_URL}/v1/candles/minutes/1"
    params = {"market": market, "count": 6}
    return _request_json(url, params)


def fetch_ticker(market: str) -> Dict:
    """Return ticker information for ``market``."""
    url = f"{BASE_URL}/v1/ticker"
    data = _request_json(url, {"markets": market})
    return data[0] if data else {}


def filter_coins(markets: List[str]) -> List[str]:
    """Filter markets by price range and 24h trade value.

    Parameters
    ----------
    markets : list[str]
        Market codes to evaluate.

    Returns
    -------
    list[str]
        Markets that satisfy the configured conditions.
    """
    selected: List[str] = []
    for market in markets:
        candles = fetch_candles(market)
        if len(candles) < 1:
            continue
        ticker = fetch_ticker(market)
        if not ticker:
            continue
        price = float(ticker.get("trade_price", 0))
        volume = float(ticker.get("acc_trade_price_24h", 0))
        use_price2 = not (PRICE2_MIN == 0 and PRICE2_MAX == 0)
        in_range = PRICE1_MIN <= price <= PRICE1_MAX
        if use_price2:
            in_range = in_range or (PRICE2_MIN <= price <= PRICE2_MAX)
        if not in_range or volume < TRADE_VALUE_MIN:
            continue
        selected.append(market)
    return selected


def select_coins() -> List[str]:
    """Return coins that meet the filter conditions."""
    markets = fetch_markets()
    return filter_coins(markets)


def save_coin_list(coins: List[str], path: Path = COIN_LIST_FILE) -> None:
    """Persist selected coins to disk.

    Parameters
    ----------
    coins : list[str]
        Symbols to save.
    path : pathlib.Path, optional
        Target file path. Defaults to :data:`COIN_LIST_FILE`.
    """
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(coins, f, ensure_ascii=False, indent=4)
        logging.info("Saved %d coins to %s", len(coins), path)
    except Exception as exc:  # pragma: no cover - best effort
        logging.error("Failed saving coin list: %s", exc)


def main() -> None:
    """Entry point used when run as a script."""
    coins = select_coins()
    if not coins:
        logging.warning("No coins matched conditions")
    save_coin_list(coins)


if __name__ == "__main__":
    main()
