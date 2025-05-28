import os
import sys
from pathlib import Path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from f3_order import utils


def test_invalid_env_logs(tmp_path, monkeypatch):
    env = tmp_path / ".env.json"
    env.write_text("{ invalid")
    key, secret = utils.load_api_keys(str(env))
    assert key == ""
    assert secret == ""
    log_path = Path("logs") / "F3_utils.log"
    assert log_path.exists()
    with log_path.open("r", encoding="utf-8") as f:
        data = f.read()
    assert "Failed to load" in data
