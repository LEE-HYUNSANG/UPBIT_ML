import importlib.util
import sys
import types
from pathlib import Path
import pytest

try:
    import pandas as pd
    pandas_available = True
except Exception:  # pragma: no cover - pandas missing
    pandas_available = False


@pytest.mark.skipif(not pandas_available, reason="pandas not available")
def test_evaluate_converts_object_columns(tmp_path):
    # Provide dummy joblib implementation
    import pickle

    dummy_joblib = types.ModuleType("joblib")

    def dump(obj, path):
        with open(path, "wb") as f:
            pickle.dump(obj, f)

    def load(path):
        with open(path, "rb") as f:
            return pickle.load(f)

    dummy_joblib.dump = dump
    dummy_joblib.load = load
    sys.modules["joblib"] = dummy_joblib

    module_path = Path(__file__).resolve().parents[1] / "f5_ml_pipeline" / "07_eval.py"
    spec = importlib.util.spec_from_file_location("eval_mod", module_path)
    eval_mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(eval_mod)

    split_dir = tmp_path / "05_split"
    model_dir = tmp_path / "06_models"
    eval_dir = tmp_path / "07_eval"
    for d in (split_dir, model_dir, eval_dir):
        d.mkdir()

    class DummyModel:
        feature_names_in_ = ["feat1", "feat2"]

        def predict(self, X):
            return (X.sum(axis=1) > 1).astype(int).to_numpy()

        def predict_proba(self, X):
            prob = X.sum(axis=1) / 2
            prob = prob.clip(0, 1)
            return pd.concat([1 - prob, prob], axis=1).to_numpy()

    model = DummyModel()
    dummy_joblib.dump(model, model_dir / "AAA_model.pkl")

    df = pd.DataFrame({
        "feat1": ["0.6", "0.4"],
        "feat2": ["0.5", "0.2"],
        "signal1": [1, 0],
        "signal2": [0, 0],
        "signal3": [0, 0],
    })
    df.to_parquet(split_dir / "AAA_test.parquet")

    eval_mod.SPLIT_DIR = split_dir
    eval_mod.MODEL_DIR = model_dir
    eval_mod.EVAL_DIR = eval_dir

    eval_mod.evaluate("AAA")

    assert (eval_dir / "AAA_metrics.json").exists()
