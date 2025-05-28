"""Convert raw 1 minute OHLCV files into cleaned Parquet files."""
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

import pandas as pd

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


def clean_one_file(input_path: Path, output_path: Path) -> None:
    """Clean a single raw OHLCV file and save it as parquet."""
    logger = logging.getLogger(__name__)

    try:
        if input_path.suffix.lower() == ".csv":
            df = pd.read_csv(input_path)
        elif input_path.suffix.lower() in [".xlsx", ".xls"]:
            df = pd.read_excel(input_path)
        else:
            logger.info("SKIP: %s", input_path.name)
            return
    except Exception as exc:  # pragma: no cover - best effort
        logger.warning("%s 로드 실패: %s", input_path.name, exc)
        return

    print(f"\n=== {input_path.name} ===")
    raw_rows = len(df)
    logger.info("원본 rows: %d", raw_rows)
    print("로드 row:", raw_rows)

    df.columns = [c.lower() for c in df.columns]

    if "timestamp" in df.columns:
        df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
        if df["timestamp"].dt.tz is None:
            df["timestamp"] = df["timestamp"].dt.tz_localize("Asia/Seoul")
        else:
            df["timestamp"] = df["timestamp"].dt.tz_convert("Asia/Seoul")

    for col in ["open", "high", "low", "close", "volume"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").astype("float32")

    # 기타 숫자형 컬럼은 가능하면 float32로 변환
    for col in df.columns:
        if col not in ["timestamp", "open", "high", "low", "close", "volume"]:
            try:
                df[col] = pd.to_numeric(df[col])
            except Exception:  # pragma: no cover - best effort
                continue
            if pd.api.types.is_numeric_dtype(df[col]):
                df[col] = df[col].astype("float32")

    # === 결측/이상치 처리 ===
    n_before = len(df)
    df = df.dropna(subset=["timestamp"])
    print("timestamp 결측 row 제거:", n_before - len(df))
    logger.info("timestamp 결측 row 제거: %d", n_before - len(df))

    df = df.sort_values("timestamp").reset_index(drop=True)

    # Drop duplicates before resampling to avoid asfreq errors
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

    # === 시계열 연속성 보장 ===
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
        prev_len = len(df)
        df = df.asfreq("1min")
        added = len(df) - prev_len
        df = df.ffill().bfill()
        df = df.reset_index()
        print("연속성 확보로 추가된 row:", added)
        logger.info("연속성 확보로 추가된 row: %d", added)

    # === 0-range/비정상값 처리 ===
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
        print("0-range row 제거:", n_before - len(df))
        logger.info("0-range row 제거: %d", n_before - len(df))

    # === 음수/중복/timestamp 정렬 ===
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

    cols = [c for c in ["timestamp", "open", "high", "low", "close", "volume"] if c in df.columns]
    df = df[cols + [c for c in df.columns if c not in cols]]

    print("클린 완료 row:", len(df))
    logger.info("클린 완료 row: %d", len(df))

    if raw_rows and len(df) <= raw_rows * 0.1:
        logger.warning("데이터가 거의 사라짐: %d -> %d", raw_rows, len(df))
        print("경고: 데이터가 거의 사라졌습니다")

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

    for file in RAW_DIR.glob("*"):
        if file.suffix.lower() not in [".csv", ".xlsx", ".xls"]:
            continue
        symbol = file.name.split("_")[0]
        output_path = CLEAN_DIR / f"{symbol}_clean.parquet"
        clean_one_file(file, output_path)


if __name__ == "__main__":
    main()
