"""03_feature_engineering 단계 스크립트."""

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

import pandas as pd

from utils import ensure_dir


CLEAN_DIR = Path("ml_data/02_clean")
FEATURE_DIR = Path("ml_data/03_feature")
LOG_PATH = Path("logs/ml_feature.log")


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


def add_features(df: pd.DataFrame) -> pd.DataFrame:
    """정제된 데이터프레임에 각종 지표 컬럼을 추가."""
    df = df.copy()

    # EMA
    df["ema5"] = df["close"].ewm(span=5, adjust=False).mean()
    df["ema20"] = df["close"].ewm(span=20, adjust=False).mean()

    # RSI
    delta = df["close"].diff()
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)
    avg_gain = gain.rolling(14).mean()
    avg_loss = loss.rolling(14).mean()
    rs = avg_gain / avg_loss
    df["rsi14"] = 100 - (100 / (1 + rs))

    # ATR
    high_low = df["high"] - df["low"]
    high_close = (df["high"] - df["close"].shift()).abs()
    low_close = (df["low"] - df["close"].shift()).abs()
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    df["atr14"] = tr.rolling(window=14).mean()

    # 볼륨 비율
    df["ma_vol20"] = df["volume"].rolling(20).mean()
    df["vol_ratio"] = df["volume"] / df["ma_vol20"]

    # 스토캐스틱
    low14 = df["low"].rolling(14).min()
    high14 = df["high"].rolling(14).max()
    df["stoch_k"] = 100 * (df["close"] - low14) / (high14 - low14)
    df["stoch_k"] = df["stoch_k"].rolling(3).mean()

    df = df.drop(columns=["ma_vol20"], errors="ignore")
    return df


def process_file(file: Path) -> None:
    """단일 파케이 파일에 피처를 추가해 저장."""
    symbol = file.name.split("_")[0]
    try:
        df = pd.read_parquet(file)
    except Exception as exc:  # pragma: no cover - best effort
        logging.warning("%s 로드 실패: %s", file.name, exc)
        return

    df = add_features(df)
    output_path = FEATURE_DIR / f"{symbol}_feature.parquet"
    try:
        df.to_parquet(output_path, index=False)
        logging.info("[FEATURE] %s → %s, shape=%s", file.name, output_path.name, df.shape)
    except Exception as exc:  # pragma: no cover - best effort
        logging.warning("%s 저장 실패: %s", output_path.name, exc)


def main() -> None:
    """실행 엔트리 포인트."""
    ensure_dir(CLEAN_DIR)
    ensure_dir(FEATURE_DIR)
    setup_logger()

    for file in CLEAN_DIR.glob("*.parquet"):
        process_file(file)


if __name__ == "__main__":
    main()

