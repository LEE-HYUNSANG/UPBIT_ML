"""Generate buy/sell labels based on trading strategy formulas.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

BASE_DIR = Path(__file__).resolve().parent
RAW_DIR = BASE_DIR / "ml_data/03_features"
LABEL_DIR = BASE_DIR / "ml_data/04_labels"
LABEL_DIR.mkdir(parents=True, exist_ok=True)

# Example strategy formulas. Extend or modify as needed.
BUY_FORMULAS = {
    "M_BREAK": lambda df: (
        (df["ema_5"] > df["ema_20"])
        & (df["ema_20"] > df["ema_60"])
        & (df["atr_14"] >= 0.04)
        & (df["vol_0"] >= df["ma_vol_20"] * 2.0)
        & (df["strength"] >= 130)
        & (df["close"] <= df["max_high_20"] * 1.001)
    ),
    "T_FLOW": lambda df: (
        (df["ema_5"] > df["ema_20"])
        & (df["ema_20"] > df["ema_60"])
        & (df["rsi_14"] > 60)
        & ((df["max_high_5"] - df["min_low_5"]) / df["min_low_5"] <= 0.01)
        & (df["atr_14"] >= 0.03)
        & (df["strength"] >= 120)
    ),
}

def _get_col(df: pd.DataFrame, name: str, default: pd.Series) -> pd.Series:
    """Return existing column or the provided default series."""
    if name in df.columns:
        return df[name]
    return default


SELL_FORMULAS = {
    "M_BREAK": lambda df: (
        (df["close"] >= _get_col(df, "entry_price", df["close"]) * 1.015)
        | (df["close"] <= _get_col(df, "peak", df["close"].cummax()) * 0.992)
        | (df["close"] <= _get_col(df, "entry_price", df["close"]) * 0.993)
        | (df["rsi_14"] < 60)
        | (df["ema_5"] < df["ema_20"])
    ),
}

def label_file(path: Path) -> None:
    """Add label columns to a single feature file."""
    print(f"Processing {path.name}")
    df = pd.read_parquet(path)
    for strat, cond in BUY_FORMULAS.items():
        df[f"buy_label_{strat}"] = cond(df).astype(int)
    for strat, cond in SELL_FORMULAS.items():
        df[f"sell_label_{strat}"] = cond(df).astype(int)
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
