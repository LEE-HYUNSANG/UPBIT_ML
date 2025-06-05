"""
[F3] 공용 유틸리티 (config 로더, 시간 등)
"""
import json
import logging
from logging.handlers import RotatingFileHandler
from common_utils import DedupFilter
import os
import math
from pathlib import Path

logger = logging.getLogger("F3_utils")
os.makedirs("logs", exist_ok=True)
fh = RotatingFileHandler(
    "logs/F3_utils.log",
    encoding="utf-8",
    maxBytes=100_000 * 1024,
    backupCount=1000,
)
formatter = logging.Formatter('%(asctime)s [F3] %(message)s')
fh.setFormatter(formatter)
logger.addHandler(fh)
logger.setLevel(logging.INFO)
logger.addFilter(DedupFilter(60))


ROOT_DIR = Path(__file__).resolve().parents[1]


def _env_paths(path: str | Path) -> list[Path]:
    """Return possible locations for ``path``."""
    p = Path(path)
    if p.is_absolute():
        return [p]
    return [p, ROOT_DIR / p]


def load_env(path: str = ".env.json") -> dict:
    """Load API keys and tokens from environment variables or ``path``.

    The function first checks the current process' environment variables and
    then loads values from ``path``. If the file is not found, the project root
    is searched as a fallback. Entries found in the JSON file override those
    from the environment.
    """
    env = dict(os.environ)
    for p in _env_paths(path):
        if not p.exists():
            continue
        try:
            with open(p, "r", encoding="utf-8") as f:
                file_env = json.load(f)
                env.update(file_env)
            log_with_tag(logger, "Loaded credentials from env.json")
            return env
        except Exception as exc:
            log_with_tag(logger, f"Failed to load {p}: {exc}")
            return env
    log_with_tag(logger, f"{path} not found; using environment only")
    return env


def load_api_keys(path: str = ".env.json") -> tuple[str, str]:
    env = load_env(path)
    key, secret = env.get("UPBIT_KEY", ""), env.get("UPBIT_SECRET", "")
    if key and secret:
        log_with_tag(logger, "Upbit credentials loaded")
    else:
        log_with_tag(logger, "UPBIT_KEY or UPBIT_SECRET missing")
    return key, secret

def load_config(path):
    """ config JSON 파일 로드 """
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"Config load error: {e}")
        return {}


def log_with_tag(logger, msg):
    """ [F3] 태그 붙여 로그 기록 """
    logger.info(f"[F3] {msg}")


def apply_tick_size(price: float, method: str = "round") -> float:
    """Return ``price`` adjusted to Upbit's KRW tick size.

    ``method`` controls the rounding strategy and can be ``"round"``, ``"ceil"`` or
    ``"floor"``.
    """
    tick = tick_size(price)
    if method == "ceil":
        return math.ceil(price / tick) * tick
    if method == "floor":
        return math.floor(price / tick) * tick
    return round(price / tick) * tick


def tick_size(price: float) -> float:
    """Return the KRW tick size for ``price``."""

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
    if price < 2000000:
        return 500
    return 1000


def pretty_symbol(symbol: str) -> str:
    """Return ``symbol`` without the market prefix like ``KRW-``."""
    if not isinstance(symbol, str):
        return symbol
    return symbol.split("-", 1)[-1]
