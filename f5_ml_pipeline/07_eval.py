"""테스트 세트를 이용해 학습된 모델을 평가한다."""

from __future__ import annotations

import json
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import (
    average_precision_score,
    brier_score_loss,
    classification_report,
    roc_auc_score,
)

from utils import ensure_dir

PIPELINE_ROOT = Path(__file__).resolve().parent
SPLIT_DIR = PIPELINE_ROOT / "ml_data" / "05_split"
MODEL_DIR = PIPELINE_ROOT / "ml_data" / "06_models"
EVAL_DIR = PIPELINE_ROOT / "ml_data" / "07_eval"
ROOT_DIR = PIPELINE_ROOT.parent
LOG_PATH = ROOT_DIR / "logs" / "F5_ml_eval.log"


# 평가 단계에서도 모델에 저장된 피처 목록을 우선 사용한다.
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

def evaluate(symbol: str) -> None:
    """단일 심볼의 모델을 평가해 JSON으로 저장."""
    test_path = SPLIT_DIR / f"{symbol}_test.parquet"
    model_path = MODEL_DIR / f"{symbol}_model.pkl"

    try:
        test_df = pd.read_parquet(test_path)
        model = joblib.load(model_path)
    except Exception as exc:  # pragma: no cover - best effort
        logging.warning("%s 평가 로드 실패: %s", symbol, exc)
        return

    # 모델이 학습에 사용한 피처 목록을 우선 사용하고, 없으면 데이터에서 추출
    features = getattr(model, "feature_names_in_", None)
    if features is None:
        features = [c for c in test_df.columns if c not in IGNORE_COLS]

    for f in features:
        if f not in test_df.columns:
            test_df[f] = 0

    for col in test_df.columns:
        if test_df[col].dtype == "object":
            converted = pd.to_numeric(test_df[col], errors="coerce")
            if pd.api.types.is_numeric_dtype(converted):
                test_df[col] = converted
    test_df.fillna(0, inplace=True)

    X_test = test_df[features]
    # ✅ label==1(익절) or label==2(트레일) 모두 성공(1)로 간주
    y_true = test_df["label"].isin([1, 2]).astype(int)

    y_pred = model.predict(X_test)
    y_prob = model.predict_proba(X_test)[:, 1]

    metrics: dict[str, float | dict[str, float]] = classification_report(
        y_true,
        y_pred,
        output_dict=True,
        zero_division=0,
    )

    if len(np.unique(y_true)) < 2:
        metrics["auc"] = 0.0
        metrics["pr_auc"] = 0.0
    else:
        try:
            metrics["auc"] = roc_auc_score(y_true, y_prob)
        except ValueError:  # pragma: no cover - safety net
            metrics["auc"] = 0.0
        metrics["pr_auc"] = average_precision_score(y_true, y_prob)
    metrics["brier"] = brier_score_loss(y_true, y_prob)

    preds = y_pred == 1
    # ✅ label==1 또는 label==2로 매매 성공 인정
    wins = preds & test_df["label"].isin([1, 2])
    metrics["win_rate"] = float(wins.sum() / preds.sum()) if preds.sum() else 0.0

    # label별 분포 추가 저장 (실전 성과 분석용)
    metrics["label_2_support"] = int((test_df["label"] == 2).sum())
    metrics["label_1_support"] = int((test_df["label"] == 1).sum())
    metrics["label_-1_support"] = int((test_df["label"] == -1).sum())
    metrics["label_0_support"] = int((test_df["label"] == 0).sum())

    # ROI/Sharpe 계산: horizon/라벨 기준 적용
    if "close" in test_df.columns:
        future_close = test_df["close"].shift(-1)
        roi = (future_close - test_df["close"]) / test_df["close"]
        trade_roi = roi[preds].fillna(0)
        metrics["avg_roi"] = float(trade_roi.mean()) if not trade_roi.empty else 0.0
        if trade_roi.std(ddof=0) != 0 and not trade_roi.empty:
            sharpe = trade_roi.mean() / trade_roi.std(ddof=0) * np.sqrt(len(trade_roi))
        else:
            sharpe = 0.0
        metrics["sharpe"] = float(sharpe)
    else:
        metrics["avg_roi"] = 0.0
        metrics["sharpe"] = 0.0

    ensure_dir(EVAL_DIR)
    metrics_path = EVAL_DIR / f"{symbol}_metrics.json"
    with open(metrics_path, "w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=2)

    logging.info("[EVAL] %s saved metrics %s (label=2 %d건)", symbol, metrics_path.name, metrics["label_2_support"])

def main() -> None:
    """실행 엔트리 포인트."""
    ensure_dir(SPLIT_DIR)
    ensure_dir(MODEL_DIR)
    ensure_dir(EVAL_DIR)
    setup_logger()

    for model_file in MODEL_DIR.glob("*_model.pkl"):
        symbol = model_file.stem.split("_")[0]
        evaluate(symbol)

if __name__ == "__main__":
    main()
