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
