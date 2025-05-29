from __future__ import annotations

import subprocess
import sys
from pathlib import Path

PIPELINE_STEPS = [
    "04_labeling.py",
    "05_split.py",
    "06_train.py",
    "07_eval.py",
    "08_predict.py",
    "09_backtest.py",
    "10_select_best_strategies.py",
]

PIPELINE_DIR = Path(__file__).resolve().parent


def run_step(step: str, index: int, total: int) -> None:
    """Execute a single pipeline step and print progress."""
    script_path = PIPELINE_DIR / step
    print(f"[{index}/{total}] Running {step} ...", flush=True)
    result = subprocess.run([sys.executable, str(script_path)])
    if result.returncode != 0:
        print(f"{step} failed with exit code {result.returncode}", flush=True)
        sys.exit(result.returncode)
    print(f"[{index}/{total}] {step} completed", flush=True)


def main() -> None:
    total = len(PIPELINE_STEPS)
    for idx, step in enumerate(PIPELINE_STEPS, start=1):
        run_step(step, idx, total)


if __name__ == "__main__":
    main()
