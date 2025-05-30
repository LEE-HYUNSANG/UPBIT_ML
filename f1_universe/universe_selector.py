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

CONFIG_PATH = "config/f1_f1_universe_filters.json"
UNIVERSE_FILE = "config/current_universe.json"
SELECTED_STRATEGIES_FILE = (
    "f5_ml_pipeline/ml_data/10_selected/selected_strategies.json"
)
MONITORING_LIST_FILE = "config/f5_f1_monitoring_list.json"
DATA_COLLECTION_LIST_FILE = "config/f1_f5_data_collection_list.json"
DATA_COLLECTION_FILTER_FILE = "config/f1_f5_data_collection_filter.json"

_UNIVERSE: List[str] = []
_LOCK = threading.Lock()


def load_monitoring_coins(path: str = MONITORING_LIST_FILE) -> List[str]:
    """Return the list of user approved monitoring coins."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):
            coins = []
            for item in data:
                if isinstance(item, dict):
                    sym = item.get("symbol")
                else:
                    sym = item
                if sym:
                    coins.append(str(sym))
            return coins
        return []
    except FileNotFoundError:
        return []
    except Exception as exc:  # pragma: no cover - best effort
        logging.error(f"Monitoring coin list 로드 실패: {exc}")
    return []


def load_data_collection_coins(path: str = DATA_COLLECTION_LIST_FILE) -> List[str]:
    """Load coin list used for data collection."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return [str(x) for x in data] if isinstance(data, list) else []
    except FileNotFoundError:
        return []
    except Exception as exc:  # pragma: no cover - best effort
        logging.error(f"Data collection coin list 로드 실패: {exc}")
    return []


def load_data_collection_filters(path: str = DATA_COLLECTION_FILTER_FILE) -> Dict:
    """Load filter conditions for data collection."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except FileNotFoundError:
        return {}
    except Exception as exc:  # pragma: no cover - best effort
        logging.error(f"Data collection filter 로드 실패: {exc}")
    return {}


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
        return {}


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
    allowed = load_monitoring_coins()
    if allowed:
        logging.info(f"모니터링 코인 리스트 로드: {allowed}")
        return allowed

    selected = load_selected_universe()
    if selected:
        logging.info(f"ML 파일에서 로드한 Universe: {selected}")
        return selected

    cached = load_universe_from_file()
    logging.info(f"캐시된 Universe 사용: {cached}")
    return cached


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


def load_selected_universe(path: str = SELECTED_STRATEGIES_FILE) -> List[str]:
    """Load symbols from the ML-selected strategies file."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):
            return [s.get("symbol") for s in data if s.get("symbol")]
    except FileNotFoundError:
        return []
    except Exception as exc:  # pragma: no cover - best effort
        logging.error(f"Selected strategies 파일 로드 실패: {exc}")
    return []


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
    allowed = load_monitoring_coins()
    if allowed:
        return allowed
    selected = load_selected_universe()
    if selected:
        return selected
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


POSITIONS_FILE = "config/f1_f3_coin_positions.json"


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
