import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from f6_setting.telegram_control import read_status, write_status


def test_read_status_defaults_to_off(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    assert read_status() == "OFF"


def test_write_and_read_status(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    write_status("ON")
    assert read_status() == "ON"
