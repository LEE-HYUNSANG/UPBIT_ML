
"""Hyperparameter tuning with Optuna's TPE sampler.

This script reads train/validation split data from ``ml_data/05_split`` and
performs hyper parameter optimisation on a LightGBM model.  The best parameters
for each symbol are written to ``ml_data/06_models/{symbol}_best_params.json``.

The code is intentionally simple so it can be adapted for different target
columns or model types.  Any missing files are skipped with a log message.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Tuple

try:
    import optuna
    import pandas as pd
    from lightgbm import LGBMClassifier
    from sklearn.metrics import roc_auc_score
except ImportError as exc:  # pragma: no cover - runtime import check
    raise SystemExit(
        "This script requires optuna, lightgbm and scikit-learn."
        " Install them via 'pip install -r requirements.txt'."
    ) from exc

BASE_DIR = Path(__file__).resolve().parent
SPLIT_DIR = BASE_DIR / "ml_data/05_split"
MODEL_DIR = BASE_DIR / "ml_data/06_models"
MODEL_DIR.mkdir(parents=True, exist_ok=True)


def _detect_label_column(df: pd.DataFrame) -> str | None:
    """Return the first column containing ``label``."""

    for col in df.columns:
        if "label" in col.lower():
            return col
    return None


def _prepare_xy(df: pd.DataFrame, label: str) -> Tuple[pd.DataFrame, pd.Series]:
    """Split dataframe into feature matrix and target column."""

    y = df[label]
    X = df.drop(columns=[label])
    # Drop non numeric columns that might confuse LightGBM
    for col in X.columns:
        if not pd.api.types.is_numeric_dtype(X[col]):
            X = X.drop(columns=[col])
    X = X.fillna(0)
    return X, y


def tune_symbol(train_path: Path, val_path: Path) -> None:
    """Tune a single symbol and write its best parameters."""

    symbol = train_path.stem.replace("_train", "")
    print(f"Tuning {symbol}")

    try:
        train_df = pd.read_parquet(train_path)
        val_df = pd.read_parquet(val_path)
    except Exception as err:
        print(f"Failed to load data for {symbol}: {err}")
        return

    label_col = _detect_label_column(train_df)
    if not label_col or label_col not in val_df.columns:
        print(
            f"Label column not found for {symbol}. "
            "Run 04_label.py and 05_split.py before tuning."
        )
        return

    X_train, y_train = _prepare_xy(train_df, label_col)
    X_val, y_val = _prepare_xy(val_df, label_col)

    def objective(trial: optuna.trial.Trial) -> float:
        params = {
            "num_leaves": trial.suggest_int("num_leaves", 31, 255),
            "learning_rate": trial.suggest_float("learning_rate", 1e-3, 0.1, log=True),
            "n_estimators": trial.suggest_int("n_estimators", 50, 500),
            "min_child_samples": trial.suggest_int("min_child_samples", 20, 200),
            "subsample": trial.suggest_float("subsample", 0.5, 1.0),
            "colsample_bytree": trial.suggest_float("colsample_bytree", 0.5, 1.0),
            "max_depth": trial.suggest_int("max_depth", -1, 16),
            "reg_alpha": trial.suggest_float("reg_alpha", 0.0, 1.0),
            "reg_lambda": trial.suggest_float("reg_lambda", 0.0, 1.0),
        }
        model = LGBMClassifier(
            **params,
            objective="binary",
            random_state=42,
            n_jobs=-1,
        )
        model.fit(X_train, y_train)
        preds = model.predict_proba(X_val)[:, 1]
        score = roc_auc_score(y_val, preds)
        return score

    study = optuna.create_study(direction="maximize", sampler=optuna.samplers.TPESampler())
    study.optimize(objective, n_trials=50, show_progress_bar=False)

    out_path = MODEL_DIR / f"{symbol}_best_params.json"
    with out_path.open("w") as f:
        json.dump(study.best_params, f, indent=2)

    summary_path = MODEL_DIR / f"{symbol}_optuna_summary.json"
    with summary_path.open("w") as f:
        json.dump({"best_value": study.best_value, "trials": len(study.trials)}, f, indent=2)

    print(f"Tuning complete for {symbol}. Best params saved to {out_path}")


def main() -> None:
    if not SPLIT_DIR.exists():
        print(f"Split directory {SPLIT_DIR} missing")
        return

    train_files = list(SPLIT_DIR.glob("*_train.parquet"))
    if not train_files:
        print(f"No train files found in {SPLIT_DIR}")
        return

    for train_path in train_files:
        val_path = SPLIT_DIR / f"{train_path.stem.replace('_train', '')}_val.parquet"
        if not val_path.exists():
            print(f"Validation file missing for {train_path.stem}")
            continue
        tune_symbol(train_path, val_path)


if __name__ == "__main__":
    main()


