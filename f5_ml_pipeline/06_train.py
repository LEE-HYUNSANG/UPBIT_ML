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

from utils import ensure_dir, load_yaml_config

# Use absolute paths relative to this file so execution works regardless of
# the current working directory.
PIPELINE_ROOT = Path(__file__).resolve().parent
SPLIT_DIR = PIPELINE_ROOT / "ml_data" / "05_split"
MODEL_DIR = PIPELINE_ROOT / "ml_data" / "06_models"
ROOT_DIR = PIPELINE_ROOT.parent
LOG_PATH = ROOT_DIR / "logs" / "F5_ml_train.log"
CONFIG_PATH = Path(__file__).parent / "config" / "train_config.yaml"
CONFIG = load_yaml_config(CONFIG_PATH)

# 학습 시 사용할 피처 목록은 데이터에 존재하는 컬럼에서 자동 추출한다.
IGNORE_COLS = {"timestamp", "label"}

def setup_logger() -> None:
    """로그 설정."""
    ensure_dir(LOG_PATH.parent)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [F5] [%(levelname)s] %(message)s",
        handlers=[
            RotatingFileHandler(
                LOG_PATH,
                encoding="utf-8",
                maxBytes=50_000 * 1024,
                backupCount=5,
            )
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

    # 학습 피처 자동 추출 - 숫자형 컬럼만 사용하도록 변환/필터링
    for df in (train_df, valid_df):
        for col in df.columns:
            if df[col].dtype == "object":
                converted = pd.to_numeric(df[col], errors="coerce")
                if pd.api.types.is_numeric_dtype(converted):
                    df[col] = converted
        df.fillna(0, inplace=True)

    numeric_cols = train_df.select_dtypes(include=["number", "bool"]).columns
    features = [c for c in numeric_cols if c not in IGNORE_COLS]
    for df in (train_df, valid_df):
        for f in features:
            if f not in df.columns:
                df[f] = 0

    # ✅ 익절(1), 트레일링스탑(2)을 모두 성공(label=1)로 간주
    y_train = train_df["label"].isin([1, 2]).astype(int)
    y_valid = valid_df["label"].isin([1, 2]).astype(int)

    if not features:
        logging.warning("%s 학습 스킵: 사용 가능한 피처가 없습니다.", symbol)
        return

    if y_train.nunique() < 2:
        logging.warning("%s 학습 스킵: 라벨이 한 종류뿐입니다.", symbol)
        return

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
    callbacks: list[lgb.callback.Callback] = []
    early_stopping_rounds = params.get("early_stopping_rounds")
    if early_stopping_rounds:
        callbacks.append(lgb.early_stopping(early_stopping_rounds))

    model.fit(
        X_train,
        y_train,
        eval_set=[(X_valid, y_valid)],
        callbacks=callbacks or None,
    )

    y_pred = model.predict(X_valid)
    y_prob = model.predict_proba(X_valid)[:, 1]

    # 평가 지표: 성공 vs 실패로 계산 (상세 분포는 별도 분석)
    metrics: dict[str, float | dict[str, float]] = classification_report(
        y_valid,
        y_pred,
        output_dict=True,
        zero_division=0,
    )
    try:
        metrics["auc"] = roc_auc_score(y_valid, y_prob)
    except ValueError:
        metrics["auc"] = 0.0
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
    logging.info("[SETUP] SPLIT_DIR=%s", SPLIT_DIR)
    logging.info("[SETUP] MODEL_DIR=%s", MODEL_DIR)
    
    for file in SPLIT_DIR.glob("*_train.parquet"):
        symbol = file.stem.split("_")[0]
        train_and_eval(symbol)

if __name__ == "__main__":
    main()
