"""학습 데이터로 머신러닝 모델을 훈련하고 저장한다."""

from __future__ import annotations

import json
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
import yaml

import joblib
import lightgbm as lgb
import pandas as pd
from sklearn.metrics import classification_report, roc_auc_score

from utils import ensure_dir

SPLIT_DIR = Path("ml_data/05_split")
MODEL_DIR = Path("ml_data/06_models")
LOG_PATH = Path("logs/ml_train.log")
CONFIG_PATH = Path(__file__).parent / "config" / "train_config.yaml"
with open(CONFIG_PATH, "r", encoding="utf-8") as f:
    CONFIG = yaml.safe_load(f)

# 학습 시 사용할 피처 목록은 데이터에 존재하는 컬럼에서 자동 추출한다.
IGNORE_COLS = {"timestamp", "label"}

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

    # 학습 피처 자동 추출
    features = [c for c in train_df.columns if c not in IGNORE_COLS]
    for df in (train_df, valid_df):
        for f in features:
            if f not in df.columns:
                df[f] = 0
        df.fillna(0, inplace=True)

    # ✅ 익절(1), 트레일링스탑(2)을 모두 성공(label=1)로 간주
    y_train = train_df["label"].isin([1, 2]).astype(int)
    y_valid = valid_df["label"].isin([1, 2]).astype(int)

    X_train = train_df[features]
    X_valid = valid_df[features]

    params = CONFIG["model"]
    model = lgb.LGBMClassifier(
        class_weight="balanced",
        learning_rate=params["learning_rate"],
        num_leaves=params["num_leaves"],
        n_estimators=params["n_estimators"],
        random_state=42,
    )
    model.fit(
        X_train,
        y_train,
        eval_set=[(X_valid, y_valid)],
        early_stopping_rounds=params.get("early_stopping_rounds"),
    )

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
