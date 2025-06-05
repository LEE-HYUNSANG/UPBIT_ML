import json
from pathlib import Path
import datetime
import time
from typing import Any, Iterable
import sys
import logging
from logging.handlers import RotatingFileHandler


def ensure_utf8_stdout() -> None:
    """Force UTF-8 encoding for stdout/stderr if possible."""
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
            sys.stderr.reconfigure(encoding="utf-8")
        except Exception:
            pass


def setup_logging(
    tag: str,
    log_files: Iterable[str | Path],
    level: int = logging.INFO,
    force: bool = True,
) -> None:
    """Configure rotating log files and console output.

    ``tag`` is included in log messages. ``log_files`` is an iterable of file
    paths to write rotating logs to.
    """
    handlers = []
    for file in log_files:
        p = Path(file)
        p.parent.mkdir(parents=True, exist_ok=True)
        handlers.append(
            RotatingFileHandler(
                p, encoding="utf-8", maxBytes=100_000 * 1024, backupCount=1000
            )
        )
    handlers.append(logging.StreamHandler())
    logging.basicConfig(
        level=level,
        format=f"%(asctime)s [{tag}] [%(levelname)s] %(message)s",
        handlers=handlers,
        force=force,
    )


def load_json(path: str | Path, default: Any = None) -> Any:
    p = Path(path)
    if not p.exists():
        return default
    try:
        with p.open("r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def save_json(path: str | Path, data: Any) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def now_kst() -> str:
    tz = datetime.timezone(datetime.timedelta(hours=9))
    return datetime.datetime.now(tz).isoformat(timespec="seconds")


def now() -> float:
    """Return current epoch timestamp as a float."""
    return time.time()

