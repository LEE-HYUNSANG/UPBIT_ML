"""새로운 데이터에 학습된 모델을 적용해 예측값을 저장한다."""

from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

import joblib
import pandas as pd

from utils import ensure_dir


MODEL_DIR = Path("ml_data/06_models")
FEATURE_DIR = Path("ml_data/03_feature")
PRED_DIR = Path("ml_data/08_pred")
LOG_PATH = Path("logs/ml_predict.log")

FEATURES = ["ema5", "ema20", "rsi14", "atr14", "vol_ratio", "stoch_k"]


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


def predict_signal(symbol: str) -> None:
    """단일 심볼의 예측을 수행해 CSV로 저장."""
    model_path = MODEL_DIR / f"{symbol}_model.pkl"
    feature_path = FEATURE_DIR / f"{symbol}_feature.parquet"

    try:
        model = joblib.load(model_path)
        df = pd.read_parquet(feature_path)
    except Exception as exc:  # pragma: no cover - best effort
        logging.warning("%s 로드 실패: %s", symbol, exc)
        return

    X = df[FEATURES]
    df["buy_signal"] = model.predict(X)
    df["buy_prob"] = model.predict_proba(X)[:, 1]

    output = df[["timestamp", "close", "buy_signal", "buy_prob"] + FEATURES]
    ensure_dir(PRED_DIR)
    output_path = PRED_DIR / f"{symbol}_pred.csv"
    try:
        output.to_csv(output_path, index=False)
        logging.info("[PREDICT] %s → %s", symbol, output_path.name)
    except Exception as exc:  # pragma: no cover - best effort
        logging.warning("%s 저장 실패: %s", output_path.name, exc)


def main() -> None:
    """실행 엔트리 포인트."""
    ensure_dir(MODEL_DIR)
    ensure_dir(FEATURE_DIR)
    ensure_dir(PRED_DIR)
    setup_logger()

    for model_file in MODEL_DIR.glob("*_model.pkl"):
        symbol = model_file.stem.split("_")[0]
        predict_signal(symbol)


if __name__ == "__main__":
    main()
