import sys
from pathlib import Path
import pandas as pd

RAW_DIR = Path(__file__).resolve().parent / "ml_data/01_raw"
CLEAN_DIR = Path(__file__).resolve().parent / "ml_data/02_clean"

COLUMN_MAP = {
    "close": ["close", "종가"],
    "open": ["open", "시가"],
    "high": ["high", "고가"],
    "low": ["low", "저가"],
    "volume": ["volume", "거래량"],
}

def detect_time_column(df: pd.DataFrame) -> str | None:
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

def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    for std, keys in COLUMN_MAP.items():
        for key in keys:
            if key in df.columns:
                df.rename(columns={key: std}, inplace=True)
                break
    return df

def clean_file(path: Path) -> None:
    print(f"Processing {path.name}")
    try:
        df = pd.read_csv(path)
        df = normalize_columns(df)
        time_col = detect_time_column(df)
        if time_col:
            df[time_col] = pd.to_datetime(df[time_col])
        df.sort_values(time_col, inplace=True)
        for col in df.columns:
            if col != time_col:
                df[col] = pd.to_numeric(df[col], errors="coerce")
        df.ffill(inplace=True)
        num_cols = df.select_dtypes(include="number").columns
        df[num_cols] = df[num_cols].fillna(0)
        if time_col:
            df.drop_duplicates(subset=time_col, inplace=True)
        else:
            df.drop_duplicates(inplace=True)
        if len(num_cols) > 0:
            df = df[~(df[num_cols].sum(axis=1) == 0)]
        if time_col:
            df.sort_values(time_col, inplace=True)
        print(df.info())
        print(df.describe(include="all"))
        out_path = CLEAN_DIR / path.with_suffix(".parquet").name
        try:
            df.to_parquet(out_path, index=False, compression="zstd")
        except Exception as e:
            print(f"Failed to write parquet with compression zstd: {e}")
            try:
                df.to_parquet(out_path, index=False)
            except Exception as e2:
                print(f"Parquet export failed: {e2}. Falling back to CSV")
                df.to_csv(out_path.with_suffix(".csv"), index=False)
                return
        print(f"Saved cleaned file to {out_path}")
    except Exception as err:
        print(f"Error processing {path.name}: {err}")

def main() -> None:
    CLEAN_DIR.mkdir(parents=True, exist_ok=True)
    if not RAW_DIR.exists():
        print(f"Raw directory {RAW_DIR} does not exist")
        return
    csv_files = list(RAW_DIR.glob("*.csv"))
    if not csv_files:
        print("No CSV files found in raw directory")
        return
    for file_path in csv_files:
        clean_file(file_path)

if __name__ == "__main__":
    main()
