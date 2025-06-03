from __future__ import annotations

import subprocess
import sys
from pathlib import Path
import json
from datetime import datetime
from common_utils import ensure_utf8_stdout
try:
    import fcntl  # POSIX only
except ImportError:  # pragma: no cover - Windows
    fcntl = None  # type: ignore
    import msvcrt
from f3_order.exception_handler import ExceptionHandler

_last_message = None


def _send_once(handler: ExceptionHandler, message: str) -> None:
    """Send a Telegram alert only if it differs from the previous one."""
    global _last_message
    if message == _last_message:
        return
    handler.send_alert(message, "info", "ml_pipeline")
    _last_message = message

PIPELINE_STEPS = [
    "02_data_cleaning.py",
    "03_feature_engineering.py",
    "04_labeling.py",
    "05_split.py",
    "06_train.py",
    "07_eval.py",
    "08_predict.py",
    "09_backtest.py",
    "10_select_best_strategies.py",
]

PIPELINE_ROOT = Path(__file__).resolve().parent

# Prevent concurrent executions which can corrupt intermediate data.
LOCK_FILE = PIPELINE_ROOT / "ml_data" / ".pipeline.lock"


def _acquire_lock() -> object:
    """Return a file handle with an exclusive lock or exit if locked."""
    LOCK_FILE.parent.mkdir(parents=True, exist_ok=True)
    try:
        fh = open(LOCK_FILE, "a+")
    except OSError:
        print("Another pipeline run is in progress. Exiting.", flush=True)
        sys.exit(0)
    try:
        if fcntl:
            fcntl.flock(fh, fcntl.LOCK_EX | fcntl.LOCK_NB)
        else:  # pragma: no cover - Windows
            msvcrt.locking(fh.fileno(), msvcrt.LK_NBLCK, 1)
    except (BlockingIOError, OSError):
        print("Another pipeline run is in progress. Exiting.", flush=True)
        if fcntl:
            fh.close()
        else:
            try:
                msvcrt.locking(fh.fileno(), msvcrt.LK_UNLCK, 1)
            finally:
                fh.close()
        sys.exit(0)
    return fh


def _release_lock(fh: object) -> None:
    """Release the lock file handle."""
    try:
        if fcntl:
            fcntl.flock(fh, fcntl.LOCK_UN)
        else:  # pragma: no cover - Windows
            msvcrt.locking(fh.fileno(), msvcrt.LK_UNLCK, 1)
    finally:
        fh.close()


def run_step(step: str, index: int, total: int) -> None:
    """Execute a single pipeline step and print progress."""
    script_path = PIPELINE_ROOT / step
    print(f"[{index}/{total}] Running {step} ...", flush=True)
    # Run each step with ``PIPELINE_DIR`` as the working directory so
    # relative paths inside the step scripts resolve correctly even if this
    # launcher is invoked from another directory.
    result = subprocess.run([sys.executable, str(script_path)], cwd=PIPELINE_ROOT)
    if result.returncode != 0:
        print(f"{step} failed with exit code {result.returncode}", flush=True)
        sys.exit(result.returncode)
    print(f"[{index}/{total}] {step} completed", flush=True)


def main() -> None:
    ensure_utf8_stdout()
    handler = ExceptionHandler({})
    lock = _acquire_lock()
    now = datetime.now().strftime("%H:%M:%S")
    _send_once(handler, f"머신러닝 학습 시작] at {now}")

    total = len(PIPELINE_STEPS)
    for idx, step in enumerate(PIPELINE_STEPS, start=1):
        run_step(step, idx, total)

    now = datetime.now().strftime("%H:%M:%S")
    selected_file = PIPELINE_ROOT / "ml_data" / "10_selected" / "selected_strategies.json"
    coins = None
    try:
        with open(selected_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):
            if data and isinstance(data[0], dict):
                symbols = [item.get("symbol") for item in data if item.get("symbol")]
            else:
                symbols = [str(item) for item in data]
            coins = ", ".join(s.split("-")[-1] for s in symbols) if symbols else None
    except Exception:
        coins = None
    _send_once(handler, f"머신러닝 학습 종료] at {now} - selected_coinList: {coins if coins else 'None'}")
    _release_lock(lock)


if __name__ == "__main__":
    main()
