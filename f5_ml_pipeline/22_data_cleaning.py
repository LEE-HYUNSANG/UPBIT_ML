"""Clean raw OHLCV files only.

This is a simplified version of :mod:`02_data_cleaning` that processes the
``ohlcv`` directory only. The cleaned output is saved under the same
``ml_data/02_clean`` path.
"""
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

import pandas as pd
from typing import List


def _aggregate_trades(df: pd.DataFrame) -> pd.DataFrame:
    """Aggregate trade data by 1 minute using mean price and sum volume."""
    if df.empty:
        return df

    df = df.copy()
    df = df.sort_values("timestamp")
    df = df.set_index("timestamp")

    agg_map = {}
    for col in df.columns:
        if "price" in col:
            agg_map[col] = "mean"
        elif "volume" in col:
            agg_map[col] = "sum"
        else:
            agg_map[col] = "last"

    return df.resample("1min").agg(agg_map).reset_index()

RAW_EXTS = {".csv", ".xlsx", ".xls", ".parquet"}

from utils import ensure_dir

# Raw files are stored directly under ``01_raw`` and contain only OHLCV data.

PIPELINE_ROOT = Path(__file__).resolve().parent
RAW_DIR = PIPELINE_ROOT / "ml_data" / "01_raw"
CLEAN_DIR = PIPELINE_ROOT / "ml_data" / "02_clean"
LOG_PATH = PIPELINE_ROOT / "logs" / "ml_clean.log"


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


def _clean_df(
    df: pd.DataFrame,
    logger: logging.Logger,
    ohlcv: bool = True,
    prefix: str | None = None,
) -> pd.DataFrame:
    """Return cleaned DataFrame using the standard rules.

    Parameters
    ----------
    df:
        Input DataFrame.
    logger:
        Logger for messages.
    ohlcv:
        If ``True`` apply OHLCV specific rules such as resampling.
    prefix:
        Optional prefix to apply to column names (except ``timestamp``).
    """

    raw_rows = len(df)
    logger.info("원본 rows: %d", raw_rows)

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
        if pd.api.types.is_numeric_dtype(df["timestamp"]):
            df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms", utc=True)
        else:
            df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True, errors="coerce")

    if ohlcv:
        required = ["timestamp", "open", "high", "low", "close", "volume"]
        for col in required:
            if col not in df.columns:
                df[col] = 0
        df = df[required + [c for c in df.columns if c not in required]]

        for col in ["open", "high", "low", "close", "volume"]:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce").astype("float32")

        for col in df.columns:
            if col not in ["timestamp", "open", "high", "low", "close", "volume"]:
                try:
                    df[col] = pd.to_numeric(df[col])
                except Exception:  # pragma: no cover - best effort
                    continue
                if pd.api.types.is_numeric_dtype(df[col]):
                    df[col] = df[col].astype("float32")

    n_before = len(df)
    df = df.dropna(subset=["timestamp"])
    logger.info("timestamp 결측 row 제거: %d", n_before - len(df))

    df = df.sort_values("timestamp").reset_index(drop=True)

    n_before = len(df)
    df = df.drop_duplicates("timestamp", keep="last")
    removed = n_before - len(df)
    if removed:
        logger.info("중복 timestamp 제거: %d", removed)

    if ohlcv:
        ohlc_cols = [c for c in ["open", "high", "low", "close"] if c in df.columns]
        if ohlc_cols:
            df[ohlc_cols] = df[ohlc_cols].ffill().bfill()
        if "volume" in df.columns:
            df["volume"] = df["volume"].fillna(0)

        if "timestamp" in df.columns:
            df = df.set_index("timestamp")
            prev_len = len(df)
            df = df.resample("1min").ffill().bfill()
            added = len(df) - prev_len
            df = df.reset_index()
            logger.info("연속성 확보로 추가된 row: %d", added)

        if ohlc_cols and "volume" in df.columns:
            n_before = len(df)
            cond = (
                (df["open"] == 0)
                & (df["high"] == 0)
                & (df["low"] == 0)
                & (df["close"] == 0)
                & (df["volume"] == 0)
            )
            df = df[~cond]
            logger.info("0-range row 제거: %d", n_before - len(df))

        for col in ["open", "high", "low", "close", "volume"]:
            if col in df.columns:
                n_before = len(df)
                df = df[df[col] >= 0]
                removed = n_before - len(df)
                if removed:
                    logger.info("%s 음수 row 제거: %d", col, removed)

    else:
        if "timestamp" in df.columns:
            df["timestamp"] = df["timestamp"].dt.round("1s")
        df = df.drop_duplicates("timestamp", keep="last")

    n_before = len(df)
    df = df.drop_duplicates("timestamp", keep="last")
    logger.info("중복 timestamp 제거: %d", n_before - len(df))

    df = df.sort_values("timestamp").reset_index(drop=True)

    if ohlcv:
        cols = [c for c in ["timestamp", "open", "high", "low", "close", "volume"] if c in df.columns]
        df = df[cols + [c for c in df.columns if c not in cols]]

    if prefix:
        df = df.rename(columns={c: f"{prefix}_{c}" for c in df.columns if c != "timestamp"})

    logger.info("클린 완료 row: %d", len(df))

    if raw_rows and len(df) <= raw_rows * 0.1:
        logger.warning("데이터가 거의 사라짐: %d -> %d", raw_rows, len(df))

    return df


def _load_concat(files: List[Path], ohlcv: bool, prefix: str | None = None) -> pd.DataFrame:
    """Load and concatenate ``files`` then clean them."""
    logger = logging.getLogger(__name__)
    dfs = []
    for f in files:
        df = _load_raw_file(f)
        if df is not None:
            dfs.append(df)
    if not dfs:
        return pd.DataFrame()
    df = pd.concat(dfs, ignore_index=True)
    return _clean_df(df, logger, ohlcv=ohlcv, prefix=prefix)


def _merge_data(
    ohlcv_df: pd.DataFrame,
    ticker_df: pd.DataFrame | None,
    order_df: pd.DataFrame | None,
    trades_df: pd.DataFrame | None,
) -> pd.DataFrame:
    """Merge ticker/orderbook with nearest timestamp and join aggregated trades."""

    merged = ohlcv_df.sort_values("timestamp").reset_index(drop=True)

    for df in [order_df, ticker_df]:
        if df is None or df.empty:
            continue
        merged = pd.merge_asof(
            merged,
            df.sort_values("timestamp"),
            on="timestamp",
            direction="nearest",
            tolerance=pd.Timedelta(minutes=1),
        )

    if trades_df is not None and not trades_df.empty:
        merged = pd.merge(
            merged,
            trades_df.sort_values("timestamp"),
            on="timestamp",
            how="left",
        )

    return merged


def clean_one_file(input_path: Path, output_path: Path, ohlcv: bool = True) -> None:
    """Clean a single raw file and save it as parquet.

    Parameters
    ----------
    input_path:
        Source file path.
    output_path:
        Destination parquet path.
    ohlcv:
        Whether the file contains OHLCV data. Non-OHLCV files skip resampling.
    """
    logger = logging.getLogger(__name__)
    df = _load_raw_file(input_path)
    if df is None:
        return

    logger.info("=== %s ===", input_path.name)
    df = _clean_df(df, logger, ohlcv=ohlcv)
    try:
        df.to_parquet(output_path, index=False)
        logger.info("Saved %s", output_path.name)
    except Exception as exc:  # pragma: no cover - best effort
        csv_fallback = output_path.with_suffix(".csv")
        df.to_csv(csv_fallback, index=False)
        logger.warning("Parquet 저장 실패 (%s), CSV 저장: %s", exc, csv_fallback.name)


def clean_merge(files: List[Path], output_path: Path) -> None:
    """Load multiple raw files, merge and clean them to ``output_path``."""
    logger = logging.getLogger(__name__)
    dfs = []
    for f in files:
        df = _load_raw_file(f)
        if df is not None:
            dfs.append(df)

    if not dfs:
        return

    logger.info("=== Merge %d files into %s ===", len(files), output_path.name)
    df = pd.concat(dfs, ignore_index=True)
    df = _clean_df(df, logger)

    try:
        df.to_parquet(output_path, index=False)
        logger.info("Saved %s", output_path.name)
    except Exception as exc:  # pragma: no cover - best effort
        csv_fallback = output_path.with_suffix(".csv")
        df.to_csv(csv_fallback, index=False)
        logger.warning("Parquet 저장 실패 (%s), CSV 저장: %s", exc, csv_fallback.name)


def clean_symbol(files: List[Path], output_dir: Path) -> None:
    """Clean OHLCV files for a single symbol."""
    if not files:
        return

    symbol = Path(files[0]).stem.split("_")[0]
    output_path = output_dir / f"{symbol}_clean.parquet"

    logger = logging.getLogger(__name__)

    ohlcv_df = _load_concat(files, True)
    if ohlcv_df.empty:
        logger.warning("%s: OHLCV 파일 없음", symbol)
        return

    try:
        ohlcv_df.to_parquet(output_path, index=False)
        logger.info("Saved %s", output_path.name)
    except Exception as exc:  # pragma: no cover - best effort
        csv_fallback = output_path.with_suffix(".csv")
        ohlcv_df.to_csv(csv_fallback, index=False)
        logger.warning("Parquet 저장 실패 (%s), CSV 저장: %s", exc, csv_fallback.name)

def main() -> None:
    """실행 엔트리 포인트."""
    ensure_dir(RAW_DIR)
    ensure_dir(CLEAN_DIR)
    setup_logger()

    file_map: dict[str, List[Path]] = {}
    for file in RAW_DIR.rglob("*"):
        if not file.is_file() or file.suffix.lower() not in RAW_EXTS:
            continue
        symbol = file.stem.split("_")[0]
        file_map.setdefault(symbol, []).append(file)

    for files in file_map.values():
        clean_symbol(files, CLEAN_DIR)


if __name__ == "__main__":
    main()
