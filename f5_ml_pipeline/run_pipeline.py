from __future__ import annotations

import subprocess
import sys
from pathlib import Path
import json
from datetime import datetime
from f3_order.exception_handler import ExceptionHandler

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
    handler = ExceptionHandler({})
    now = datetime.now().strftime("%Y%m%d %H:%M:%S")
    handler.send_alert(f"머신러닝 학습 시작] @{now}", "info", "ml_pipeline")

    total = len(PIPELINE_STEPS)
    for idx, step in enumerate(PIPELINE_STEPS, start=1):
        run_step(step, idx, total)

    now = datetime.now().strftime("%Y%m%d %H:%M:%S")
    selected_file = PIPELINE_ROOT / "ml_data" / "10_selected" / "selected_strategies.json"
    coins = None
    try:
        with open(selected_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        coins = ",".join(data) if isinstance(data, list) else None
    except Exception:
        coins = None
    handler.send_alert(
        f"머신러닝 학습 종료] @{now} - selected_coinList: {coins if coins else 'None'}",
        "info",
        "ml_pipeline",
    )


if __name__ == "__main__":
    main()
