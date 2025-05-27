"""Train LightGBM models using pre-tuned hyperparameters."""

from __future__ import annotations

import json
from pathlib import Path
from typing import List, Tuple, Dict

try:
    import pandas as pd
    import joblib
    from lightgbm import LGBMClassifier
    from sklearn.metrics import accuracy_score, f1_score, roc_auc_score
except ImportError as exc:  # pragma: no cover - runtime import check
    raise SystemExit(
        "This script requires lightgbm and scikit-learn. Install them via 'pip install -r requirements.txt'."
    ) from exc

BASE_DIR = Path(__file__).resolve().parent
SPLIT_DIR = BASE_DIR / "ml_data/05_split"
MODEL_DIR = BASE_DIR / "ml_data/06_models"
MODEL_DIR.mkdir(parents=True, exist_ok=True)


def _detect_label_columns(df: pd.DataFrame) -> List[str]:
    """Return columns that look like labels."""
    return [c for c in df.columns if "label" in c.lower()]


def _prepare_xy(df: pd.DataFrame, label: str) -> Tuple[pd.DataFrame, pd.Series]:
    """Split dataframe into X and y while removing non numeric columns."""
    y = df[label]
    X = df.drop(columns=[label])
    for col in X.columns:
        if not pd.api.types.is_numeric_dtype(X[col]):
            X = X.drop(columns=[col])
    X = X.fillna(0)
    return X, y


def _evaluate(y_true: pd.Series, preds: List[float]) -> Dict[str, float]:
    """Return standard binary classification metrics."""
    auc = roc_auc_score(y_true, preds)
    pred_labels = [1 if p >= 0.5 else 0 for p in preds]
    acc = accuracy_score(y_true, pred_labels)
    f1 = f1_score(y_true, pred_labels)
    return {"auc": auc, "accuracy": acc, "f1": f1}


def train_symbol(train_path: Path, val_path: Path, test_path: Path) -> None:
    """Train models for all labels of a single symbol."""
    symbol = train_path.stem.replace("_train", "")
    print(f"Training models for {symbol}")

    try:
        train_df = pd.read_parquet(train_path)
        val_df = pd.read_parquet(val_path)
        test_df = pd.read_parquet(test_path)
    except Exception as err:
        print(f"Failed to load data for {symbol}: {err}")
        return

    labels = _detect_label_columns(train_df)
    if not labels:
        print(f"No label columns found for {symbol}")
        return

    for label_col in labels:
        if label_col not in val_df.columns or label_col not in test_df.columns:
            print(f"Label {label_col} missing in splits for {symbol}")
            continue

        params_path = MODEL_DIR / f"{symbol}_{label_col}_best_params.json"
        if not params_path.exists():
            print(f"Best params not found for {symbol} [{label_col}]")
            continue

        with params_path.open() as f:
            best_params = json.load(f)

        train_all = pd.concat([train_df, val_df], ignore_index=True)
        X_train, y_train = _prepare_xy(train_all, label_col)
        model = LGBMClassifier(
            **best_params,
            objective="binary",
            random_state=42,
            n_jobs=-1,
        )
        model.fit(X_train, y_train)

        X_test, y_test = _prepare_xy(test_df, label_col)
        preds = model.predict_proba(X_test)[:, 1]
        metrics = _evaluate(y_test, preds)

        model_path = MODEL_DIR / f"{symbol}_{label_col}_model.pkl"
        joblib.dump(model, model_path)

        metrics_path = MODEL_DIR / f"{symbol}_{label_col}_metrics.json"
        with metrics_path.open("w") as f:
            json.dump(metrics, f, indent=2)

        if hasattr(model, "booster_"):
            booster = model.booster_
            imp = booster.feature_importance(importance_type="gain")
            names = booster.feature_name()
        else:  # pragma: no cover - fallback
            imp = model.feature_importances_
            names = model.feature_name_
        fi_df = pd.DataFrame({"feature": names, "importance": imp})
        fi_df.sort_values(by="importance", ascending=False, inplace=True)
        fi_path = MODEL_DIR / f"{symbol}_{label_col}_feature_importance.csv"
        fi_df.to_csv(fi_path, index=False)
        print(
            f"Model for {symbol} [{label_col}] saved to {model_path}. AUC={metrics['auc']:.4f}"
        )


def main() -> None:
    if not SPLIT_DIR.exists():
        print(f"Split directory {SPLIT_DIR} missing")
        return

    train_files = list(SPLIT_DIR.glob("*_train.parquet"))
    if not train_files:
        print(f"No train files found in {SPLIT_DIR}")
        return

    for train_path in train_files:
        base = train_path.stem.replace("_train", "")
        val_path = SPLIT_DIR / f"{base}_val.parquet"
        test_path = SPLIT_DIR / f"{base}_test.parquet"
        if not val_path.exists() or not test_path.exists():
            print(f"Validation or test file missing for {base}")
            continue
        train_symbol(train_path, val_path, test_path)


if __name__ == "__main__":
    main()
