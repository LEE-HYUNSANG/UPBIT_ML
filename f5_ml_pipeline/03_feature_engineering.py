"""03_feature_engineering 단계 확장형 스크립트."""

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
    """정제된 데이터프레임에 각종 지표/파생 컬럼을 추가."""
    df = df.copy()
    df.columns = [c.lower() for c in df.columns]

    required = {"open", "high", "low", "close", "volume"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Missing required columns: {', '.join(sorted(missing))}")

    # === 표준 피처 ===

    # EMA
    df["ema5"] = df["close"].ewm(span=5, adjust=False).mean()
    df["ema8"] = df["close"].ewm(span=8, adjust=False).mean()
    df["ema13"] = df["close"].ewm(span=13, adjust=False).mean()
    df["ema20"] = df["close"].ewm(span=20, adjust=False).mean()
    df["ema21"] = df["close"].ewm(span=21, adjust=False).mean()

    # EMA 차이
    df["ema5_ema20_diff"] = df["ema5"] - df["ema20"]
    df["ema8_ema21_diff"] = df["ema8"] - df["ema21"]

    # RSI
    for w in [7, 14, 21]:
        delta = df["close"].diff()
        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)
        avg_gain = gain.rolling(w).mean()
        avg_loss = loss.rolling(w).mean()
        rs = avg_gain / avg_loss
        df[f"rsi{w}"] = 100 - (100 / (1 + rs))

    # ATR
    for w in [7, 14]:
        high_low = df["high"] - df["low"]
        high_close = (df["high"] - df["close"].shift()).abs()
        low_close = (df["low"] - df["close"].shift()).abs()
        tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        df[f"atr{w}"] = tr.rolling(window=w).mean()

    # 볼륨 평균/비율
    df["ma_vol5"] = df["volume"].rolling(5).mean()
    df["ma_vol20"] = df["volume"].rolling(20).mean()
    df["vol_ratio"] = df["volume"] / df["ma_vol20"]
    df["vol_ratio_5"] = df["volume"] / df["ma_vol5"]

    # 스토캐스틱
    for w in [7, 14]:
        low_w = df["low"].rolling(w).min()
        high_w = df["high"].rolling(w).max()
        df[f"stoch_k{w}"] = 100 * (df["close"] - low_w) / (high_w - low_w)
        df[f"stoch_k{w}"] = df[f"stoch_k{w}"].rolling(3).mean()

    # === 추가 파생 피처/캔들/변동률/볼린저 ===

    # 가격변동률(1, 5, 10분)
    for p in [1, 5, 10]:
        df[f"pct_change_{p}m"] = df["close"].pct_change(p)

    # 캔들(양봉/음봉, 바디비율, 고저차)
    df["is_bull"] = (df["close"] > df["open"]).astype(int)
    df["body_size"] = (df["close"] - df["open"]).abs()
    df["body_pct"] = df["body_size"] / (df["high"] - df["low"]).replace(0, 1)
    df["hl_range"] = df["high"] - df["low"]
    df["oc_range"] = (df["open"] - df["close"]).abs()

    # 볼린저밴드(20, 표준 2배수)
    ma20 = df["close"].rolling(20).mean()
    std20 = df["close"].rolling(20).std()
    df["bb_upper"] = ma20 + 2 * std20
    df["bb_lower"] = ma20 - 2 * std20
    df["bb_width"] = (df["bb_upper"] - df["bb_lower"]) / ma20
    df["bb_dist"] = (df["close"] - ma20) / std20

    # 결측치/이상치 대체
    df = df.drop(columns=["ma_vol5", "ma_vol20"], errors="ignore")
    df = df.replace([float('inf'), float('-inf')], pd.NA)
    df = df.ffill().bfill()

    return df


def process_file(file: Path) -> None:
    """단일 파케이 파일에 피처를 추가해 저장."""
    symbol = file.name.split("_")[0]
    try:
        df = pd.read_parquet(file)
    except Exception as exc:
        logging.warning("%s 로드 실패: %s", file.name, exc)
        return

    try:
        df = add_features(df)
        output_path = FEATURE_DIR / f"{symbol}_feature.parquet"
        df.to_parquet(output_path, index=False)
        logging.info("[FEATURE] %s → %s, shape=%s", file.name, output_path.name, df.shape)
    except Exception as exc:
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
