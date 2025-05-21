import json
import os
import shutil
from typing import List, Dict


STRATEGY_FILE = "config/strategy.json"
DEFAULT_FILE = "config/default_strategy.json"
BACKUP_FILE = "config/strategy_backup.json"


def load_strategy_list(path: str = STRATEGY_FILE) -> List[Dict]:
    """전략 설정 리스트를 읽어 반환한다."""
    target = path if os.path.exists(path) else DEFAULT_FILE
    with open(target, encoding="utf-8") as f:
        return json.load(f)


def save_strategy_list(data: List[Dict], path: str = STRATEGY_FILE) -> None:
    """전략 설정 리스트를 저장한다."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def restore_defaults(
    default_path: str = DEFAULT_FILE,
    path: str = STRATEGY_FILE,
    backup_path: str = BACKUP_FILE,
) -> None:
    """기본 전략 파일을 복원한다."""
    if os.path.exists(path) and not os.path.exists(backup_path):
        shutil.copy2(path, backup_path)
    shutil.copy2(default_path, path)
