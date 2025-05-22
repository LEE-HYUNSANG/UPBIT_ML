from helpers.logger import log_trade, log_config_change, get_recent_logs
import os


def test_log_trade(tmp_path):
    path = tmp_path / "log.csv"
    log_trade("trade", {"action": "buy", "coin": "BTC", "price": 1}, path=str(path))
    logs = get_recent_logs(1)
    assert logs[0]["action"] == "buy"
    assert path.exists()


def test_log_config_change(tmp_path):
    path = tmp_path / "conf.csv"
    log_config_change("funds", "buy_amount", 1, 2, path=str(path))
    assert path.exists()
    with open(path, encoding="utf-8") as f:
        lines = f.readlines()
    assert len(lines) == 2  # header + row

