"""Generate buy and sell labels for all strategies."""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

BASE_DIR = Path(__file__).resolve().parent
# Allow running this script directly from the repository root by making
# package imports resolvable.
sys.path.insert(0, str(BASE_DIR.parent))

from f5_ml_pipeline.strategy_loader import load_strategies
RAW_DIR = BASE_DIR / "ml_data/03_features"
LABEL_DIR = BASE_DIR / "ml_data/04_labels"
LABEL_DIR.mkdir(parents=True, exist_ok=True)

STRATEGIES = load_strategies()


def label_file(path: Path) -> None:
    """Apply all strategy formulas to a single feature file."""
    print(f"Processing {path.name}")
    df = pd.read_parquet(path)

    if "entry_price" not in df.columns:
        df["entry_price"] = df["close"]
    if "peak" not in df.columns:
        df["peak"] = df["close"].cummax()
    if "exit_price" not in df.columns:
        df["exit_price"] = df["close"]

    for code, funcs in STRATEGIES.items():
        df[f"buy_label_{code}"] = funcs["buy"](df).astype(int)
        df[f"sell_label_{code}"] = funcs["sell"](df).astype(int)

    out_path = LABEL_DIR / path.name
    df.to_parquet(out_path, index=False, compression="zstd")
    print(f"Saved label to {out_path}")


def main() -> None:
    files = list(RAW_DIR.glob("*.parquet"))
    if not files:
        print("No features files found in", RAW_DIR)
        return
    for file in files:
        label_file(file)


if __name__ == "__main__":
    main()
