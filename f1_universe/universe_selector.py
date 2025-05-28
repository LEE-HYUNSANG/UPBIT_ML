"""거래 대상 종목을 선정하기 위한 유틸리티 모음입니다.

Upbit REST API에서 데이터를 받아 사용자 설정 필터를 적용하여
모니터링할 최종 종목 리스트를 구축합니다.
네트워크가 없으면 실제 호출은 실패하지만, 로직 자체는 그대로 동작합니다.
"""

from __future__ import annotations

import json
import os
import threading
import time
from typing import Dict, List

import logging
from logging.handlers import RotatingFileHandler
import requests

os.makedirs("logs", exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [F1] [%(levelname)s] %(message)s",
    handlers=[
        RotatingFileHandler(
            "logs/F1_signal_engine.log",
            encoding="utf-8",
            maxBytes=100_000 * 1024,
            backupCount=1000,
        ),
        logging.StreamHandler(),
    ],
)

BASE_URL = "https://api.upbit.com/v1"
CONFIG_PATH = "config/universe.json"
UNIVERSE_FILE = "config/current_universe.json"

_UNIVERSE: List[str] = []
_LOCK = threading.Lock()


def load_config(path: str = CONFIG_PATH) -> Dict:
    """Universe 필터 설정을 로드합니다.

    Parameters
    ----------
    path : str
        JSON 설정 파일 경로

    Returns
    -------
    dict
        설정 값 딕셔너리. 파일이 없으면 기본값을 반환합니다.
    """
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        # 템플릿 모달창 기본값과 유사한 기본 설정값
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
        logging.error(f"[F1][API] 요청 실패: {url} | params={params} | {exc}")
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
        ticker_data = _fetch_json(
            f"{BASE_URL}/ticker", {"markets": ",".join(chunk)}
        )

        # 티커마다 요청하지 않고 묶음 단위로 호가 정보를 조회
        orderbook_data = _fetch_json(
            f"{BASE_URL}/orderbook", {"markets": ",".join(chunk)}
        )
        orderbook_map = {d.get("market", ""): d for d in orderbook_data}

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

            ob = orderbook_map.get(item.get("market"))
            if ob and ob.get("orderbook_units"):
                ask = ob["orderbook_units"][0].get("ask_price", price)
                bid = ob["orderbook_units"][0].get("bid_price", price)
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
    try:
        with open(UNIVERSE_FILE, "w", encoding="utf-8") as f:
            json.dump(universe, f, ensure_ascii=False, indent=2)
    except Exception as exc:  # pragma: no cover - best effort
        logging.error(f"Universe 파일 저장 실패: {exc}")
    logging.info(f"Universe updated: {universe}")


def load_universe_from_file(path: str = UNIVERSE_FILE) -> List[str]:
    """Load the cached universe from ``path`` and populate the global list."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):
            with _LOCK:
                _UNIVERSE.clear()
                _UNIVERSE.extend(data)
            return list(data)
    except FileNotFoundError:
        return []
    except Exception as exc:  # pragma: no cover - best effort
        logging.error(f"Universe 파일 로드 실패: {exc}")
    return []


def get_universe() -> List[str]:
    """Return the last cached universe."""
    with _LOCK:
        if _UNIVERSE:
            return list(_UNIVERSE)
    return load_universe_from_file()


def schedule_universe_updates(interval: int = 1800, config: Dict | None = None) -> None:
    """Start a background thread refreshing the universe periodically."""

    def _loop() -> None:
        while True:
            try:
                update_universe(config)
            except Exception as exc:  # pragma: no cover - best effort
                logging.error(f"Universe 갱신 실패: {exc}")
            time.sleep(interval)

    thread = threading.Thread(target=_loop, daemon=True)
    thread.start()


POSITIONS_FILE = "config/coin_positions.json"


def init_coin_positions(threshold: float = 5000.0, path: str = POSITIONS_FILE) -> None:
    """Fetch account balances and store holdings above ``threshold``.

    Parameters
    ----------
    threshold : float
        Minimum evaluation amount in KRW to register a coin as a position.
    path : str
        File path to write the positions JSON list.
    """

    from f3_order.upbit_api import UpbitClient

    client = UpbitClient()
    try:
        accounts = client.get_accounts()
    except Exception as exc:  # pragma: no cover - network best effort
        logging.error(f"[F1][INIT] 계좌 조회 실패: {exc}")
        return

    try:
        with open(path, "r", encoding="utf-8") as f:
            existing = json.load(f)
    except FileNotFoundError:
        existing = []
    except Exception as exc:  # pragma: no cover - best effort
        logging.error(f"[F1][INIT] 포지션 파일 로드 실패: {exc}")
        existing = []

    open_syms = {p.get("symbol") for p in existing if p.get("status") == "open"}
    new_positions = []

    for coin in accounts:
        if coin.get("currency") == "KRW":
            continue
        bal = float(coin.get("balance", 0))
        price = float(coin.get("avg_buy_price", 0))
        eval_amt = bal * price
        if eval_amt < threshold:
            continue
        symbol = f"{coin.get('unit_currency', 'KRW')}-{coin.get('currency')}"
        if symbol in open_syms:
            continue
        pos = {
            "symbol": symbol,
            "entry_time": time.time(),
            "entry_price": price,
            "qty": bal,
            "pyramid_count": 0,
            "avgdown_count": 0,
            "status": "open",
            "origin": "imported",
            "strategy": "imported",
        }
        logging.info(f"[F1][INIT] Import position {symbol} Eval={int(eval_amt):,}")
        new_positions.append(pos)

    if new_positions:
        existing.extend(new_positions)
        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                json.dump(existing, f, ensure_ascii=False, indent=2)
        except Exception as exc:  # pragma: no cover - best effort
            logging.error(f"[F1][INIT] 포지션 저장 실패: {exc}")
