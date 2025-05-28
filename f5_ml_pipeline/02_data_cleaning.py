"""02_data_cleaning 단계 스크립트."""
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

import pandas as pd

from utils import ensure_dir

RAW_DIR = Path("ml_data/01_raw")
CLEAN_DIR = Path("ml_data/02_clean")
LOG_PATH = Path("logs/ml_clean.log")


def setup_logger() -> None:
    """로그 설정."""
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
    """단일 파일 전처리."""
    try:
        if input_path.suffix.lower() == ".csv":
            df = pd.read_csv(input_path)
        elif input_path.suffix.lower() in [".xlsx", ".xls"]:
            df = pd.read_excel(input_path)
        else:
            logging.info("SKIP: %s", input_path.name)
            return
    except Exception as exc:  # pragma: no cover - best effort
        logging.warning("%s 로드 실패: %s", input_path.name, exc)
        return

    raw_rows = len(df)
    df.columns = [c.lower() for c in df.columns]
    if "timestamp" in df.columns:
        df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True, errors="coerce")

    for col in ["open", "high", "low", "close", "volume"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").astype("float32")

    for col in df.columns:
        if col != "timestamp" and col not in ["open", "high", "low", "close", "volume"]:
            df[col] = pd.to_numeric(df[col], errors="ignore")
            if pd.api.types.is_numeric_dtype(df[col]):
                df[col] = df[col].astype("float32")

    if "timestamp" in df.columns:
        df = df.drop_duplicates("timestamp")
        df = df.set_index("timestamp").sort_index()
        df = df.asfreq("1min")
        df = df.ffill().bfill()
        df = df.reset_index()

    df = df[~((df.get("open") == 0) & (df.get("high") == 0) & (df.get("low") == 0) & (df.get("close") == 0))]
    if "volume" in df.columns:
        df = df[df["volume"] > 0]

    for col in ["open", "high", "low", "close", "volume"]:
        if col in df.columns:
            df = df[df[col] >= 0]

    df = df.sort_values("timestamp").reset_index(drop=True)

    deleted_rows = raw_rows - len(df)
    logging.info("%s 정제 완료: %d -> %d rows", input_path.name, raw_rows, len(df))
    if deleted_rows:
        logging.info("삭제된 행 수: %d", deleted_rows)

    try:
        df.to_parquet(output_path, index=False)
        logging.info("Saved %s", output_path.name)
    except Exception as exc:  # pragma: no cover - best effort
        csv_fallback = output_path.with_suffix(".csv")
        df.to_csv(csv_fallback, index=False)
        logging.warning("Parquet 저장 실패 (%s), CSV 저장: %s", exc, csv_fallback.name)


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
