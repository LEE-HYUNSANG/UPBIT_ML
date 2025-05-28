import logging
import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from f3_order.utils import load_env


def test_invalid_env_logs_warning(tmp_path, caplog):
    env_path = tmp_path / ".env.json"
    env_path.write_text("{invalid")
    with caplog.at_level(logging.WARNING, logger="F3_utils"):
        load_env(str(env_path))
    assert any("Failed to load" in m for m in caplog.messages)
