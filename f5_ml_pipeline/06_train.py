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

# 최신 피처 리스트, 03_feature_engineering.py와 1:1로 일치해야 함
FEATURES = [
    "ema5", "ema8", "ema13", "ema20", "ema21", "ema5_ema20_diff", "ema8_ema21_diff",
    "rsi7", "rsi14", "rsi21",
    "atr7", "atr14",
    "vol_ratio", "vol_ratio_5",
    "stoch_k7", "stoch_k14",
    "pct_change_1m", "pct_change_5m", "pct_change_10m",
    "is_bull", "body_size", "body_pct", "hl_range", "oc_range",
    "bb_upper", "bb_lower", "bb_width", "bb_dist"
]

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

    # 결측 피처 자동 보정 (새 컬럼 추가되었을 때 오류 방지)
    for f in FEATURES:
        for df in (train_df, valid_df):
            if f not in df.columns:
                df[f] = 0

    # ✅ 익절(1), 트레일링스탑(2)을 모두 성공(label=1)로 간주
    y_train = train_df["label"].isin([1, 2]).astype(int)
    y_valid = valid_df["label"].isin([1, 2]).astype(int)

    X_train = train_df[FEATURES]
    X_valid = valid_df[FEATURES]

    model = lgb.LGBMClassifier(class_weight="balanced", n_estimators=200, random_state=42)
    model.fit(X_train, y_train)

    y_pred = model.predict(X_valid)
    y_prob = model.predict_proba(X_valid)[:, 1]

    # 평가 지표: 성공 vs 실패로 계산 (상세 분포는 별도 분석)
    metrics: dict[str, float | dict[str, float]] = classification_report(
        y_valid,
        y_pred,
        output_dict=True,
    )
    metrics["auc"] = roc_auc_score(y_valid, y_prob)
    metrics["label_2_support"] = int((valid_df["label"] == 2).sum())
    metrics["label_1_support"] = int((valid_df["label"] == 1).sum())
    metrics["label_-1_support"] = int((valid_df["label"] == -1).sum())
    metrics["label_0_support"] = int((valid_df["label"] == 0).sum())

    ensure_dir(MODEL_DIR)
    model_path = MODEL_DIR / f"{symbol}_model.pkl"
    joblib.dump(model, model_path)

    metrics_path = MODEL_DIR / f"{symbol}_metrics.json"
    with open(metrics_path, "w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=2)

    logging.info(
        "[TRAIN] %s saved model %s and metrics %s (label=2 %d건)",
        symbol, model_path.name, metrics.get("accuracy"), metrics["label_2_support"]
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
