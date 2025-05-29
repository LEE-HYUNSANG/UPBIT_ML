"""Convert raw 1 minute OHLCV files into cleaned Parquet files."""
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

import pandas as pd
from typing import List

RAW_EXTS = {".csv", ".xlsx", ".xls", ".parquet"}


from utils import ensure_dir

RAW_DIR = Path("ml_data/01_raw")
CLEAN_DIR = Path("ml_data/02_clean")
LOG_PATH = Path("logs/ml_clean.log")


def setup_logger() -> None:
    """Configure rotating file logger."""
    ensure_dir(LOG_PATH.parent)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            RotatingFileHandler(
                LOG_PATH,
                encoding="utf-8",
                maxBytes=50_000 * 1024,
                backupCount=5,
            ),
            logging.StreamHandler(),
        ],
        force=True,
    )


def _load_raw_file(path: Path) -> pd.DataFrame | None:
    """Load CSV, Excel or Parquet file as DataFrame."""
    logger = logging.getLogger(__name__)
    try:
        ext = path.suffix.lower()
        if ext == ".csv":
            return pd.read_csv(path)
        if ext in {".xlsx", ".xls"}:
            return pd.read_excel(path)
        if ext == ".parquet":
            return pd.read_parquet(path)
        logger.info("SKIP: %s", path.name)
    except Exception as exc:  # pragma: no cover - best effort
        logger.warning("%s 로드 실패: %s", path.name, exc)
    return None


def _clean_df(df: pd.DataFrame, logger: logging.Logger, ohlcv: bool) -> pd.DataFrame:
    """Return cleaned DataFrame using the standard rules.

    Parameters
    ----------
    df : pd.DataFrame
        Raw dataframe to clean.
    logger : logging.Logger
        Logger for debug messages.
    ohlcv : bool
        Whether the input contains OHLCV fields. Non-OHLCV data skips price specific logic.
    """
    raw_rows = len(df)
    logger.info("원본 rows: %d", raw_rows)
    print("로드 row:", raw_rows)

    col_map = {
        "opening_price": "open",
        "high_price": "high",
        "low_price": "low",
        "trade_price": "close",
        "candle_acc_trade_volume": "volume",
        "candle_date_time_utc": "timestamp",
    }

    df = df.rename(columns=col_map)
    df.columns = [c.lower() for c in df.columns]
    if df.columns.duplicated().any():
        logger.warning("중복 컬럼 존재: %s", df.columns[df.columns.duplicated()].tolist())
        for col in df.columns[df.columns.duplicated()].unique():
            dup_cols = [c for c in df.columns if c == col]
            df[col] = df[dup_cols].bfill(axis=1).iloc[:, 0]
        df = df.loc[:, ~df.columns.duplicated()]

    if "timestamp" in df.columns:
        df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce", utc=True)
        df["timestamp"] = df["timestamp"].dt.round("1s")

    required = ["timestamp"] + (["open", "high", "low", "close", "volume"] if ohlcv else [])
    for col in required:
        if col not in df.columns:
            df[col] = 0 if ohlcv and col != "timestamp" else pd.NA
    df = df[required + [c for c in df.columns if c not in required]]

    numeric_cols = [c for c in ["open", "high", "low", "close", "volume"] if c in df.columns] if ohlcv else []
    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce").astype("float32")

    for col in df.columns:
        if col not in required:
            try:
                df[col] = pd.to_numeric(df[col])
            except Exception:  # pragma: no cover - best effort
                continue
            if pd.api.types.is_numeric_dtype(df[col]):
                df[col] = df[col].astype("float32")

    n_before = len(df)
    df = df.dropna(subset=["timestamp"])
    print("timestamp 결측 row 제거:", n_before - len(df))
    logger.info("timestamp 결측 row 제거: %d", n_before - len(df))

    df = df.sort_values("timestamp").reset_index(drop=True)

    n_before = len(df)
    df = df.drop_duplicates("timestamp", keep="last")
    removed = n_before - len(df)
    if removed:
        print("중복 timestamp 제거:", removed)
        logger.info("중복 timestamp 제거: %d", removed)

    ohlc_cols = [c for c in ["open", "high", "low", "close"] if c in df.columns]
    if ohlc_cols:
        df[ohlc_cols] = df[ohlc_cols].ffill().bfill()
    if "volume" in df.columns:
        df["volume"] = df["volume"].fillna(0)

    if ohlcv and "timestamp" in df.columns:
        df = df.set_index("timestamp")
        prev_len = len(df)
        df = df.resample("1min").ffill().bfill()
        added = len(df) - prev_len
        df = df.reset_index()
        print("연속성 확보로 추가된 row:", added)
        logger.info("연속성 확보로 추가된 row: %d", added)

    if ohlcv and ohlc_cols and "volume" in df.columns:
        n_before = len(df)
        cond = (
            (df["open"] == 0)
            & (df["high"] == 0)
            & (df["low"] == 0)
            & (df["close"] == 0)
            & (df["volume"] == 0)
        )
        df = df[~cond]
        print("0-range row 제거:", n_before - len(df))
        logger.info("0-range row 제거: %d", n_before - len(df))

    if ohlcv:
        for col in ["open", "high", "low", "close", "volume"]:
            if col in df.columns:
                n_before = len(df)
                df = df[df[col] >= 0]
                removed = n_before - len(df)
                if removed:
                    print(f"{col} 음수 row 제거:", removed)
                    logger.info("%s 음수 row 제거: %d", col, removed)

    n_before = len(df)
    df = df.drop_duplicates("timestamp", keep="last")
    print("중복 timestamp 제거:", n_before - len(df))
    logger.info("중복 timestamp 제거: %d", n_before - len(df))

    df = df.sort_values("timestamp").reset_index(drop=True)

    cols = [c for c in required if c in df.columns]
    df = df[cols + [c for c in df.columns if c not in cols]]

    print("클린 완료 row:", len(df))
    logger.info("클린 완료 row: %d", len(df))

    if raw_rows and len(df) <= raw_rows * 0.1:
        logger.warning("데이터가 거의 사라짐: %d -> %d", raw_rows, len(df))
        print("경고: 데이터가 거의 사라졌습니다")

    return df


def clean_one_file(input_path: Path, output_path: Path, ohlcv: bool) -> None:
    """Clean a single raw data file and save it as parquet."""
    logger = logging.getLogger(__name__)
    df = _load_raw_file(input_path)
    if df is None:
        return

    print(f"\n=== {input_path.name} ===")
    df = _clean_df(df, logger, ohlcv)

    try:
        df.to_parquet(output_path, index=False)
        logger.info("Saved %s", output_path.name)
    except Exception as exc:  # pragma: no cover - best effort
        csv_fallback = output_path.with_suffix(".csv")
        df.to_csv(csv_fallback, index=False)
        logger.warning("Parquet 저장 실패 (%s), CSV 저장: %s", exc, csv_fallback.name)


def clean_merge(files: List[Path], output_path: Path, ohlcv: bool) -> None:
    """Load multiple raw files, merge and clean them to ``output_path``."""
    logger = logging.getLogger(__name__)
    dfs = []
    for f in files:
        df = _load_raw_file(f)
        if df is not None:
            dfs.append(df)

    if not dfs:
        return

    print(f"\n=== Merge {len(files)} files into {output_path.name} ===")
    df = pd.concat(dfs, ignore_index=True)
    df = _clean_df(df, logger, ohlcv)

    try:
        df.to_parquet(output_path, index=False)
        logger.info("Saved %s", output_path.name)
    except Exception as exc:  # pragma: no cover - best effort
        csv_fallback = output_path.with_suffix(".csv")
        df.to_csv(csv_fallback, index=False)
        logger.warning("Parquet 저장 실패 (%s), CSV 저장: %s", exc, csv_fallback.name)


def main() -> None:
    """실행 엔트리 포인트."""
    ensure_dir(RAW_DIR)
    ensure_dir(CLEAN_DIR)
    setup_logger()

    file_map: dict[tuple[str, str], List[Path]] = {}
    for file in RAW_DIR.rglob("*"):
        if not file.is_file() or file.suffix.lower() not in RAW_EXTS:
            continue
        rel = file.relative_to(RAW_DIR)
        data_type = rel.parts[0] if len(rel.parts) > 1 else "ohlcv"
        symbol = file.stem.split("_")[0]
        file_map.setdefault((data_type, symbol), []).append(file)

    for (data_type, symbol), files in file_map.items():
        out_dir = CLEAN_DIR / data_type
        ensure_dir(out_dir)
        output_path = out_dir / f"{symbol}_clean.parquet"
        is_ohlcv = data_type == "ohlcv"
        if len(files) == 1:
            clean_one_file(files[0], output_path, is_ohlcv)
        else:
            clean_merge(sorted(files), output_path, is_ohlcv)


if __name__ == "__main__":
    main()
