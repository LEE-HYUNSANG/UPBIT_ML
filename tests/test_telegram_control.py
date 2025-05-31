import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from f6_setting import remote_control


def test_read_status_defaults_to_off(tmp_path, monkeypatch):
    monkeypatch.setenv("SERVER_STATUS_FILE", str(tmp_path / "server_status.txt"))
    assert remote_control.read_status() == "OFF"


def test_write_and_read_status(tmp_path, monkeypatch):
    path = tmp_path / "server_status.txt"
    monkeypatch.setenv("SERVER_STATUS_FILE", str(path))
    remote_control.write_status("ON")
    assert remote_control.read_status() == "ON"
