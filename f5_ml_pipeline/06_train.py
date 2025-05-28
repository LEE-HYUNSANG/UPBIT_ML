"""학습 데이터로 머신러닝 모델을 훈련하고 저장한다."""

from __future__ import annotations

import json
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

import joblib
import lightgbm as lgb
import pandas as pd
from sklearn.metrics import classification_report, roc_auc_score

from utils import ensure_dir


SPLIT_DIR = Path("ml_data/05_split")
MODEL_DIR = Path("ml_data/06_models")
LOG_PATH = Path("logs/ml_train.log")

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


def train_and_eval(symbol: str) -> None:
    """단일 심볼의 모델을 학습하고 저장한다."""
    train_path = SPLIT_DIR / f"{symbol}_train.parquet"
    valid_path = SPLIT_DIR / f"{symbol}_valid.parquet"

    try:
        train_df = pd.read_parquet(train_path)
        valid_df = pd.read_parquet(valid_path)
    except Exception as exc:  # pragma: no cover - best effort
        logging.warning("%s 데이터 로드 실패: %s", symbol, exc)
        return

    X_train = train_df[FEATURES]
    y_train = (train_df["label"] == 1).astype(int)
    X_valid = valid_df[FEATURES]
    y_valid = (valid_df["label"] == 1).astype(int)

    model = lgb.LGBMClassifier(class_weight="balanced", n_estimators=200, random_state=42)
    model.fit(X_train, y_train)

    y_pred = model.predict(X_valid)
    y_prob = model.predict_proba(X_valid)[:, 1]

    metrics: dict[str, float | dict[str, float]] = classification_report(
        y_valid,
        y_pred,
        output_dict=True,
    )
    metrics["auc"] = roc_auc_score(y_valid, y_prob)

    ensure_dir(MODEL_DIR)
    model_path = MODEL_DIR / f"{symbol}_model.pkl"
    joblib.dump(model, model_path)

    metrics_path = MODEL_DIR / f"{symbol}_metrics.json"
    with open(metrics_path, "w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=2)

    logging.info(
        "[TRAIN] %s saved model %s and metrics %s", symbol, model_path.name, metrics.get("accuracy")
    )


def main() -> None:
    """실행 엔트리 포인트."""
    ensure_dir(SPLIT_DIR)
    ensure_dir(MODEL_DIR)
    setup_logger()

    for file in SPLIT_DIR.glob("*_train.parquet"):
        symbol = file.stem.split("_")[0]
        train_and_eval(symbol)


if __name__ == "__main__":
    main()

