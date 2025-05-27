"""Calibrate predicted probabilities of trained models using isotonic regression."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Tuple

try:
    import pandas as pd
    import joblib
    from sklearn.isotonic import IsotonicRegression
    from sklearn.metrics import accuracy_score, f1_score, roc_auc_score, brier_score_loss
except ImportError as exc:  # pragma: no cover - runtime import check
    raise SystemExit(
        "This script requires scikit-learn. Install it via 'pip install -r requirements.txt'."
    ) from exc

BASE_DIR = Path(__file__).resolve().parent
SPLIT_DIR = BASE_DIR / "ml_data/05_split"
MODEL_DIR = BASE_DIR / "ml_data/06_models"
MODEL_DIR.mkdir(parents=True, exist_ok=True)


def _detect_label_columns(df: pd.DataFrame) -> List[str]:
    """Return columns that look like labels."""
    return [c for c in df.columns if "label" in c.lower()]


def _prepare_xy(df: pd.DataFrame, label: str) -> Tuple[pd.DataFrame, pd.Series]:
    """Split dataframe into feature matrix and target column."""
    y = df[label]
    X = df.drop(columns=[label])
    for col in X.columns:
        if not pd.api.types.is_numeric_dtype(X[col]):
            X = X.drop(columns=[col])
    X = X.fillna(0)
    return X, y


def _evaluate(y_true: pd.Series, probs: List[float], thresh: float) -> Dict[str, float]:
    """Return evaluation metrics for ``probs`` at ``thresh``."""
    auc = roc_auc_score(y_true, probs)
    brier = brier_score_loss(y_true, probs)
    preds = [1 if p >= thresh else 0 for p in probs]
    acc = accuracy_score(y_true, preds)
    f1 = f1_score(y_true, preds)
    return {"auc": auc, "brier": brier, "accuracy": acc, "f1": f1}


def _find_best_threshold(y_true: pd.Series, probs: List[float]) -> float:
    """Return the probability threshold that maximises F1."""
    best_thresh = 0.5
    best_f1 = 0.0
    for t in [x / 100.0 for x in range(1, 100)]:
        preds = [1 if p >= t else 0 for p in probs]
        f1 = f1_score(y_true, preds)
        if f1 > best_f1:
            best_f1 = f1
            best_thresh = t
    return best_thresh


def calibrate_symbol(val_path: Path, test_path: Path) -> None:
    """Calibrate all label models for a single symbol."""
    symbol = val_path.stem.replace("_val", "")
    print(f"Calibrating {symbol}")

    model_files = list(MODEL_DIR.glob(f"{symbol}_*_model.pkl"))
    if not model_files:
        print(f"No trained models found for {symbol}")
        return

    try:
        val_df = pd.read_parquet(val_path)
        test_df = pd.read_parquet(test_path)
    except Exception as err:
        print(f"Failed to load data for {symbol}: {err}")
        return

    for model_file in model_files:
        label_col = model_file.stem.replace(f"{symbol}_", "").replace("_model", "")
        if label_col not in val_df.columns or label_col not in test_df.columns:
            print(f"Label {label_col} missing in splits for {symbol}")
            continue

        model = joblib.load(model_file)
        X_val, y_val = _prepare_xy(val_df, label_col)
        X_test, y_test = _prepare_xy(test_df, label_col)

        raw_val = model.predict_proba(X_val)[:, 1]
        raw_test = model.predict_proba(X_test)[:, 1]

        iso = IsotonicRegression(out_of_bounds="clip")
        iso.fit(raw_val, y_val)

        cal_val = iso.predict(raw_val)
        cal_test = iso.predict(raw_test)

        thresh = _find_best_threshold(y_val, cal_val)

        metrics = {
            "before": _evaluate(y_test, raw_test, 0.5),
            "after": _evaluate(y_test, cal_test, thresh),
            "threshold": thresh,
        }

        calib_path = MODEL_DIR / f"{symbol}_{label_col}_calib.pkl"
        joblib.dump(iso, calib_path)

        metrics_path = MODEL_DIR / f"{symbol}_{label_col}_calib_metrics.json"
        with metrics_path.open("w") as f:
            json.dump(metrics, f, indent=2)

        thresh_path = MODEL_DIR / f"{symbol}_{label_col}_thresh.json"
        with thresh_path.open("w") as f:
            json.dump({"threshold": thresh}, f, indent=2)

        print(
            f"Calibration for {symbol} [{label_col}] saved to {calib_path}. "
            f"AUC(before)={metrics['before']['auc']:.4f} -> "
            f"AUC(after)={metrics['after']['auc']:.4f}"
        )


def main() -> None:
    if not SPLIT_DIR.exists():
        print(f"Split directory {SPLIT_DIR} missing")
        return

    val_files = list(SPLIT_DIR.glob("*_val.parquet"))
    if not val_files:
        print(f"No validation files found in {SPLIT_DIR}")
        return

    for val_path in val_files:
        base = val_path.stem.replace("_val", "")
        test_path = SPLIT_DIR / f"{base}_test.parquet"
        if not test_path.exists():
            print(f"Test file missing for {base}")
            continue
        calibrate_symbol(val_path, test_path)


if __name__ == "__main__":
    main()
