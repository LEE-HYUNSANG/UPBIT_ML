import os
import sys
import types
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from f3_order.order_executor import _buy_list_lock


def test_unlock_seeks_to_start(tmp_path, monkeypatch):
    path = tmp_path / "lock.json"
    path.write_text("[]")

    positions = []

    def fake_locking(fd, mode, n):
        positions.append(os.lseek(fd, 0, os.SEEK_CUR))

    monkeypatch.setattr("f3_order.order_executor.fcntl", None)
    monkeypatch.setattr(
        "f3_order.order_executor.msvcrt",
        types.SimpleNamespace(LK_LOCK=1, LK_UNLCK=2, locking=fake_locking),
        raising=False,
    )

    with _buy_list_lock(path) as fh:
        fh.read()

    assert positions == [0, 0]


def test_lock_can_be_disabled(tmp_path, monkeypatch):
    path = tmp_path / "lock.json"
    path.write_text("[]")

    def raising(*args, **kwargs):
        raise AssertionError("locking called")

    monkeypatch.setattr("f3_order.order_executor.fcntl", None)
    monkeypatch.setattr(
        "f3_order.order_executor.msvcrt",
        types.SimpleNamespace(LK_LOCK=1, LK_UNLCK=2, locking=raising),
        raising=False,
    )
    monkeypatch.setenv("UPBIT_DISABLE_LOCKS", "1")

    with _buy_list_lock(path) as fh:
        fh.write("x")

    monkeypatch.delenv("UPBIT_DISABLE_LOCKS")
    assert "x" in path.read_text()
