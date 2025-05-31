import os
import shutil
from pathlib import Path


def clear_logs() -> None:
    """Delete all files and subdirectories under the logs folder."""
    log_root = Path(__file__).resolve().parent
    for path in log_root.iterdir():
        if path.name == 'relog.py':
            continue
        if path.is_file() or path.is_symlink():
            path.unlink(missing_ok=True)
        elif path.is_dir():
            shutil.rmtree(path, ignore_errors=True)
    # recreate empty directories for runtime use
    for name in [
        'debug',
        'info',
        'warning',
        'error',
        'critical',
        'f1',
        'f2',
        'f3',
        'f4',
        'f5',
        'f6',
        'etc',
    ]:
        (log_root / name).mkdir(parents=True, exist_ok=True)


if __name__ == '__main__':
    clear_logs()
