# 공통 함수/유틸
import time
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from datetime import datetime


def now() -> float:
    """Return current epoch timestamp as a floating point number."""
    return time.time()


def setup_ml_logger(step: int) -> logging.Logger:
    """Create ML pipeline logger with rotating file handler.

    Parameters
    ----------
    step : int
        Pipeline step number used in the log prefix.
    """
    log_dir = Path(__file__).resolve().parent / "ml_data/09_logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    log_file = log_dir / f"mllog_{timestamp}.log"
    logger = logging.getLogger(f"ML_{step:02d}")
    logger.setLevel(logging.INFO)
    if not logger.handlers:
        handler = RotatingFileHandler(
            log_file, maxBytes=1_000_000, backupCount=10, encoding="utf-8"
        )
        formatter = logging.Formatter("[%(name)s]: %(message)s")
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    return logger


