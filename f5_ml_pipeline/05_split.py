"""Split labelled feature datasets into train/validation/test sets in chronological order."""

from __future__ import annotations

import sys
from pathlib import Path

from F5_utils import setup_ml_logger
logger = setup_ml_logger(5)

import pandas as pd

BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR.parent))

FEATURE_DIR = BASE_DIR / "ml_data/04_labels"
SPLIT_DIR = BASE_DIR / "ml_data/05_split"

# Default split ratios. Update here to change dataset proportions.
TRAIN_RATIO = 0.7
VAL_RATIO = 0.15
TEST_RATIO = 0.15


def _detect_time_column(df: pd.DataFrame) -> str | None:
    """Return the name of the timestamp column if present."""
    candidates = [c for c in df.columns if "time" in c or "date" in c]
    for col in [
        "timestamp",
        "candle_date_time_utc",
        "candle_date_time_kst",
        "datetime",
    ] + candidates:
        if col in df.columns:
            return col
    return None


def _split_dataframe(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Split ``df`` while preserving time order."""
    n = len(df)
    if n == 0:
        return df, df, df

    train_end = int(n * TRAIN_RATIO)
    val_end = int(n * (TRAIN_RATIO + VAL_RATIO))

    if n >= 3:
        train_end = max(train_end, 1)
        val_end = max(val_end, train_end + 1)
        val_end = min(val_end, n - 1)
    elif n == 2:
        train_end = 1
        val_end = 1
    else:  # n == 1
        train_end = 1
        val_end = 1

    train_df = df.iloc[:train_end]
    val_df = df.iloc[train_end:val_end]
    test_df = df.iloc[val_end:]
    return train_df, val_df, test_df


def process_file(path: Path) -> None:
    logger.info(f"Splitting {path.name}")
    try:
        df = pd.read_parquet(path)
    except Exception as err:
        logger.info(f"Failed to read {path.name}: {err}")
        return

    time_col = _detect_time_column(df)
    if time_col:
        df.sort_values(time_col, inplace=True)
        df.reset_index(drop=True, inplace=True)

    train_df, val_df, test_df = _split_dataframe(df)

    stem = path.stem
    for subset, suffix in [
        (train_df, "_train"),
        (val_df, "_val"),
        (test_df, "_test"),
    ]:
        out_path = SPLIT_DIR / f"{stem}{suffix}.parquet"
        try:
            subset.to_parquet(out_path, index=False, compression="zstd")
        except Exception as err:
            logger.info(f"Failed to save {out_path.name}: {err}")
            continue
        logger.info(f"Saved {out_path.name}")


def main() -> None:
    SPLIT_DIR.mkdir(parents=True, exist_ok=True)
    if not FEATURE_DIR.exists():
        logger.info(f"Feature directory {FEATURE_DIR} missing")
        return

    files = list(FEATURE_DIR.glob("*.parquet"))
    if not files:
        logger.info("No feature files found")
        return

    for file in files:
        process_file(file)


if __name__ == "__main__":
    main()
