import os
import sys
import json
import importlib.util

MODULE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "f5_ml_pipeline"))
sys.path.insert(0, MODULE_DIR)
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

MODULE_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "f5_ml_pipeline", "10_select_best_strategies.py")
)
spec = importlib.util.spec_from_file_location("select_best", MODULE_PATH)
select_best = importlib.util.module_from_spec(spec)
spec.loader.exec_module(select_best)


def test_passes_criteria_basic():
    summary = {
        "win_rate": 0.6,
        "avg_roi": 0.003,
        "sharpe": 1.2,
        "mdd": -0.05,
        "total_entries": 60,
    }
    assert select_best.passes_criteria(summary)


def test_select_strategies(tmp_path):
    summary_dir = tmp_path / "09_backtest"
    param_dir = tmp_path / "04_label"
    summary_dir.mkdir()
    param_dir.mkdir()

    sample_summary = {
        "win_rate": 0.6,
        "avg_roi": 0.003,
        "sharpe": 1.3,
        "mdd": -0.05,
        "total_entries": 60,
    }
    (summary_dir / "AAA_summary.json").write_text(json.dumps(sample_summary))
    (param_dir / "AAA_best_params.json").write_text(json.dumps({"p": 1}))

    select_best.SUMMARY_DIR = summary_dir
    select_best.PARAM_DIR = param_dir
    select_best.TOP_N = 1

    strategies = select_best.select_strategies()
    assert len(strategies) == 1
    assert strategies[0]["symbol"] == "AAA"
    assert strategies[0]["params"] == {"p": 1}
