"""새로운 데이터에 학습된 모델을 적용해 예측값을 저장한다."""

from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

import joblib
import pandas as pd

from utils import ensure_dir

PIPELINE_ROOT = Path(__file__).resolve().parent
MODEL_DIR = PIPELINE_ROOT / "ml_data" / "06_models"
FEATURE_DIR = PIPELINE_ROOT / "ml_data" / "03_feature"
PRED_DIR = PIPELINE_ROOT / "ml_data" / "08_pred"
ROOT_DIR = PIPELINE_ROOT.parent
LOG_PATH = ROOT_DIR / "logs" / "f5" / "F5_ml_predict.log"

# 모델 저장 시 포함된 피처 목록을 우선 사용한다.
IGNORE_COLS = {"timestamp"}

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

    features = getattr(model, "feature_names_in_", None)
    if features is None:
        features = [c for c in df.columns if c not in IGNORE_COLS]


    for f in features:
        if f not in df.columns:
            df[f] = 0

    for col in df.columns:
        if df[col].dtype == "object":
            converted = pd.to_numeric(df[col], errors="coerce")
            if pd.api.types.is_numeric_dtype(converted):
                df[col] = converted
    df.fillna(0, inplace=True)

    X = df[features]
    df["buy_signal"] = model.predict(X)
    df["buy_prob"] = model.predict_proba(X)[:, 1]

    # (옵션) buy_signal==1은 "익절 또는 트레일 수익 패턴" 예측
    output_cols = ["timestamp", "close", "buy_signal", "buy_prob"] + list(features)
    output = df[output_cols] if all(c in df.columns for c in output_cols) else df

    ensure_dir(PRED_DIR)
    output_path = PRED_DIR / f"{symbol}_pred.csv"
    try:
        output.to_csv(output_path, index=False)
        logging.info("[PREDICT] %s → %s (총 %d건, 신호 %d건)", symbol, output_path.name, len(df), (df["buy_signal"] == 1).sum())
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
