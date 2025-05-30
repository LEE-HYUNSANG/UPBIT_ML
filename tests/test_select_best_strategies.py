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


def test_main_writes_monitoring(tmp_path):
    summary_dir = tmp_path / "09_backtest"
    param_dir = tmp_path / "04_label"
    out_dir = tmp_path / "10_selected"
    conf_dir = tmp_path / "config"
    summary_dir.mkdir()
    param_dir.mkdir()
    out_dir.mkdir()
    conf_dir.mkdir()

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
    select_best.OUT_DIR = out_dir
    select_best.OUT_FILE = out_dir / "selected_strategies.json"
    select_best.MONITORING_LIST_FILE = conf_dir / "coin_list_monitoring.json"
    select_best.LOG_PATH = tmp_path / "select.log"
    select_best.TOP_N = 1

    select_best.main()

    data = json.loads((conf_dir / "coin_list_monitoring.json").read_text())
    assert data == ["AAA"]

    log_text = (tmp_path / "select.log").read_text()
    assert "monitoring list updated" in log_text


def test_main_clears_files_when_empty(tmp_path):
    summary_dir = tmp_path / "09_backtest"
    param_dir = tmp_path / "04_label"
    out_dir = tmp_path / "10_selected"
    conf_dir = tmp_path / "config"
    summary_dir.mkdir()
    param_dir.mkdir()
    out_dir.mkdir()
    conf_dir.mkdir()

    select_best.SUMMARY_DIR = summary_dir
    select_best.PARAM_DIR = param_dir
    select_best.OUT_DIR = out_dir
    select_best.OUT_FILE = out_dir / "selected_strategies.json"
    select_best.MONITORING_LIST_FILE = conf_dir / "coin_list_monitoring.json"
    select_best.LOG_PATH = tmp_path / "select.log"

    select_best.main()

    out_data = json.loads((out_dir / "selected_strategies.json").read_text())
    mon_data = json.loads((conf_dir / "coin_list_monitoring.json").read_text())
    assert out_data == []
    assert mon_data == []


def test_main_overwrites_existing_files(tmp_path):
    summary_dir = tmp_path / "09_backtest"
    param_dir = tmp_path / "04_label"
    out_dir = tmp_path / "10_selected"
    conf_dir = tmp_path / "config"
    summary_dir.mkdir()
    param_dir.mkdir()
    out_dir.mkdir()
    conf_dir.mkdir()

    (out_dir / "selected_strategies.json").write_text(json.dumps([{"a": 1}]))
    (conf_dir / "coin_list_monitoring.json").write_text(json.dumps(["AAA"]))

    select_best.SUMMARY_DIR = summary_dir
    select_best.PARAM_DIR = param_dir
    select_best.OUT_DIR = out_dir
    select_best.OUT_FILE = out_dir / "selected_strategies.json"
    select_best.MONITORING_LIST_FILE = conf_dir / "coin_list_monitoring.json"
    select_best.LOG_PATH = tmp_path / "select.log"

    select_best.main()

    out_data = json.loads((out_dir / "selected_strategies.json").read_text())
    mon_data = json.loads((conf_dir / "coin_list_monitoring.json").read_text())
    assert out_data == []
    assert mon_data == []
