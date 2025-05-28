"""04_labeling 단계 스크립트."""

from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

import pandas as pd

from utils import ensure_dir


FEATURE_DIR = Path("ml_data/03_feature")
LABEL_DIR = Path("ml_data/04_label")
LOG_PATH = Path("logs/ml_label.log")

DEFAULT_HORIZON = 30
DEFAULT_THRESH_PCT = 0.003


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


def make_labels(
    df: pd.DataFrame,
    horizon: int = DEFAULT_HORIZON,
    thresh_pct: float = DEFAULT_THRESH_PCT,
) -> pd.DataFrame:
    """주어진 OHLC 데이터프레임에서 매매 라벨을 생성한다."""
    df = df.copy()
    labels: list[int] = []
    close = df["close"].values
    high = df["high"].values
    low = df["low"].values

    for i in range(len(df) - horizon):
        entry = close[i]
        max_high = high[i + 1 : i + 1 + horizon].max()
        min_low = low[i + 1 : i + 1 + horizon].min()
        if max_high >= entry * (1 + thresh_pct):
            labels.append(1)
        elif min_low <= entry * (1 - thresh_pct):
            labels.append(-1)
        else:
            labels.append(0)

    for _ in range(horizon):
        labels.append(0)

    df["label"] = labels
    return df


def process_file(file: Path, horizon: int, thresh_pct: float) -> None:
    """단일 피처 파일을 읽어 라벨을 생성 후 저장."""
    symbol = file.name.split("_")[0]
    try:
        df = pd.read_parquet(file)
    except Exception as exc:  # pragma: no cover - best effort
        logging.warning("%s 로드 실패: %s", file.name, exc)
        return

    df = make_labels(df, horizon=horizon, thresh_pct=thresh_pct)
    output_path = LABEL_DIR / f"{symbol}_label.parquet"
    try:
        df.to_parquet(output_path, index=False)
        dist = df["label"].value_counts().to_dict()
        logging.info("[LABEL] %s → %s, shape=%s, dist=%s", file.name, output_path.name, df.shape, dist)
    except Exception as exc:  # pragma: no cover - best effort
        logging.warning("%s 저장 실패: %s", output_path.name, exc)


def main(horizon: int = DEFAULT_HORIZON, thresh_pct: float = DEFAULT_THRESH_PCT) -> None:
    """실행 엔트리 포인트."""
    ensure_dir(FEATURE_DIR)
    ensure_dir(LABEL_DIR)
    setup_logger()

    for file in FEATURE_DIR.glob("*.parquet"):
        process_file(file, horizon, thresh_pct)


if __name__ == "__main__":
    main()
