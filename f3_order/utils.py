"""
[F3] 공용 유틸리티 (config 로더, 시간 등)
"""
import json
import datetime
import logging
from logging.handlers import RotatingFileHandler
import os

logger = logging.getLogger("F3_utils")
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


def load_env(path: str = ".env.json") -> dict:
    """Load API keys and tokens from environment variables or ``path``.

    The function first checks the current process' environment variables and
    then loads values from ``path`` if the file exists. Entries found in the
    JSON file override those from the environment.
    """
    env = dict(os.environ)
    if not os.path.exists(path):
        logger.info(f"{path} not found. Using environment variables only.")
        return env
    try:
        with open(path, "r", encoding="utf-8") as f:
            file_env = json.load(f)
            env.update(file_env)
    except Exception as exc:  # pragma: no cover - invalid json
        logger.warning(f"Failed to load {path}: {exc}")
    return env


def load_api_keys(path: str = ".env.json") -> tuple[str, str]:
    env = load_env(path)
    key = env.get("UPBIT_KEY", "")
    secret = env.get("UPBIT_SECRET", "")
    if key and secret:
        logger.info("Upbit API credentials loaded")
    else:
        logger.warning("UPBIT_KEY or UPBIT_SECRET missing. Check .env.json or environment variables.")
    return key, secret

def load_config(path):
    """ config JSON 파일 로드 """
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"Config load error: {e}")
        return {}

def now():
    """ 현재 UTC+9(한국) 타임스탬프 반환 (isoformat) """
    return (datetime.datetime.utcnow() + datetime.timedelta(hours=9)).isoformat()

def log_with_tag(logger, msg):
    """ [F3] 태그 붙여 로그 기록 """
    logger.info(f"[F3] {msg}")
