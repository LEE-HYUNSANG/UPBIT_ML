
"""Hyperparameter tuning with Optuna's TPE sampler.

This script reads train/validation split data from ``ml_data/05_split`` and
performs hyper parameter optimisation on a LightGBM model.  For each symbol and
label column a study is executed and the following artefacts are produced under
``ml_data/06_models``:

``{symbol}_{label}_best_params.json``
    The best hyperparameters found during optimisation.
``{symbol}_{label}_model.pkl``
    LightGBM model retrained on the full train+validation set.
``{symbol}_{label}_optuna_study.pkl``
    The Optuna ``Study`` object for later analysis.
``{symbol}_{label}_feature_importance.csv``
    Sorted feature importance as reported by LightGBM.
``optuna_tuning_summary.csv``
    Aggregate table containing results for all tuned symbols/labels.

The code is intentionally simple so it can be adapted for different target
columns or model types.  Any missing files are skipped with a log message.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import List, Tuple

try:
    import optuna
    import pandas as pd
    import joblib
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


def _detect_label_columns(df: pd.DataFrame) -> List[str]:
    """Return all columns containing ``label`` (case-insensitive)."""

    return [c for c in df.columns if "label" in c.lower()]


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


def tune_symbol(train_path: Path, val_path: Path) -> List[dict]:
    """Tune all label columns for a single symbol."""

    symbol = train_path.stem.replace("_train", "")
    print(f"Tuning {symbol}")

    try:
        train_df = pd.read_parquet(train_path)
        val_df = pd.read_parquet(val_path)
    except Exception as err:
        print(f"Failed to load data for {symbol}: {err}")
        return []

    labels = _detect_label_columns(train_df)
    if not labels:
        print(
            f"Label column not found for {symbol}. "
            "Run 04_label.py and 05_split.py before tuning."
        )
        return []

    results = []
    for label_col in labels:
        if label_col not in val_df.columns:
            print(f"Label {label_col} missing in validation set for {symbol}")
            continue

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

        params_path = MODEL_DIR / f"{symbol}_{label_col}_best_params.json"
        with params_path.open("w") as f:
            json.dump(study.best_params, f, indent=2)

        study_path = MODEL_DIR / f"{symbol}_{label_col}_optuna_study.pkl"
        joblib.dump(study, study_path)

        X_all, y_all = _prepare_xy(pd.concat([train_df, val_df], ignore_index=True), label_col)
        final_model = LGBMClassifier(
            **study.best_params,
            objective="binary",
            random_state=42,
            n_jobs=-1,
        )
        final_model.fit(X_all, y_all)
        model_path = MODEL_DIR / f"{symbol}_{label_col}_model.pkl"
        joblib.dump(final_model, model_path)

        if hasattr(final_model, "booster_"):
            booster = final_model.booster_
            imp = booster.feature_importance(importance_type="gain")
            names = booster.feature_name()
        else:  # pragma: no cover - fallback
            imp = final_model.feature_importances_
            names = final_model.feature_name_
        fi_df = pd.DataFrame({"feature": names, "importance": imp})
        fi_df.sort_values(by="importance", ascending=False, inplace=True)
        fi_path = MODEL_DIR / f"{symbol}_{label_col}_feature_importance.csv"
        fi_df.to_csv(fi_path, index=False)

        print(f"Tuning complete for {symbol} [{label_col}]. Model saved to {model_path}")
        results.append(
            {
                "symbol": symbol,
                "label": label_col,
                "best_metric": study.best_value,
                "n_trials": len(study.trials),
                "best_params": json.dumps(study.best_params),
            }
        )

    return results


def main() -> None:
    if not SPLIT_DIR.exists():
        print(f"Split directory {SPLIT_DIR} missing")
        return

    train_files = list(SPLIT_DIR.glob("*_train.parquet"))
    if not train_files:
        print(f"No train files found in {SPLIT_DIR}")
        return

    results: List[dict] = []
    for train_path in train_files:
        val_path = SPLIT_DIR / f"{train_path.stem.replace('_train', '')}_val.parquet"
        if not val_path.exists():
            print(f"Validation file missing for {train_path.stem}")
            continue
        results.extend(tune_symbol(train_path, val_path))

    if results:
        summary_csv = MODEL_DIR / "optuna_tuning_summary.csv"
        if summary_csv.exists():
            summary_df = pd.read_csv(summary_csv)
        else:
            summary_df = pd.DataFrame(columns=["symbol", "label", "best_metric", "n_trials", "best_params"])
        summary_df = pd.concat([summary_df, pd.DataFrame(results)], ignore_index=True)
        summary_df.drop_duplicates(subset=["symbol", "label"], keep="last", inplace=True)
        summary_df.to_csv(summary_csv, index=False)
        print(f"Summary written to {summary_csv}")


if __name__ == "__main__":
    main()


