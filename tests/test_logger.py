from helpers.logger import log_trade, get_recent_logs
import os


def test_log_trade(tmp_path):
    path = tmp_path / "log.csv"
    log_trade("trade", {"action": "buy", "coin": "BTC", "price": 1}, path=str(path))
    logs = get_recent_logs(1)
    assert logs[0]["action"] == "buy"
    assert path.exists()

