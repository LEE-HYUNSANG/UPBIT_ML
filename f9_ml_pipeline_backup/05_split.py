"""라벨 데이터를 학습/검증/테스트 세트로 분할한다."""

from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

import pandas as pd

from utils import ensure_dir

# Absolute paths relative to this file so the script behaves the same
# regardless of the current working directory.
PIPELINE_ROOT = Path(__file__).resolve().parent
LABEL_DIR = PIPELINE_ROOT / "ml_data" / "04_label"
SPLIT_DIR = PIPELINE_ROOT / "ml_data" / "05_split"
LOG_PATH = PIPELINE_ROOT / "logs" / "ml_split.log"


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


def time_split(
    df: pd.DataFrame, train_ratio: float = 0.7, valid_ratio: float = 0.2
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """시간순으로 학습/검증/테스트 세트를 분할."""
    n = len(df)
    n_train = int(n * train_ratio)
    n_valid = int(n * valid_ratio)
    train = df.iloc[:n_train]
    valid = df.iloc[n_train : n_train + n_valid]
    test = df.iloc[n_train + n_valid :]
    return train, valid, test


def process_file(file: Path, train_ratio: float, valid_ratio: float) -> None:
    """단일 라벨 파일을 분할해 저장."""
    symbol = file.name.split("_")[0]
    try:
        df = pd.read_parquet(file)
    except Exception as exc:  # pragma: no cover - best effort
        logging.warning("%s 로드 실패: %s", file.name, exc)
        return

    train, valid, test = time_split(df, train_ratio=train_ratio, valid_ratio=valid_ratio)

    for split_df, suffix in (
        (train, "train"),
        (valid, "valid"),
        (test, "test"),
    ):
        output_path = SPLIT_DIR / f"{symbol}_{suffix}.parquet"
        try:
            split_df.to_parquet(output_path, index=False)
            dist = split_df.get("label", pd.Series()).value_counts().to_dict()
            logging.info(
                "[SPLIT] %s → %s, shape=%s, dist=%s",
                file.name,
                output_path.name,
                split_df.shape,
                dist,
            )
        except Exception as exc:  # pragma: no cover - best effort
            logging.warning("%s 저장 실패: %s", output_path.name, exc)


def main(train_ratio: float = 0.7, valid_ratio: float = 0.2) -> None:
    """실행 엔트리 포인트."""
    ensure_dir(LABEL_DIR)
    ensure_dir(SPLIT_DIR)
    setup_logger()
    logging.info("[SETUP] LABEL_DIR=%s", LABEL_DIR)
    logging.info("[SETUP] SPLIT_DIR=%s", SPLIT_DIR)

    for file in LABEL_DIR.glob("*.parquet"):
        process_file(file, train_ratio, valid_ratio)


if __name__ == "__main__":
    main()
