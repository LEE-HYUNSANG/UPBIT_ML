# -*- coding: utf-8 -*-
"""트레이드 및 이벤트 로그 기록 모듈."""

from __future__ import annotations

import csv
import os
from collections import deque
from datetime import datetime
from typing import Any, Dict

# 최근 n건 로그를 메모리에 보관한다
_recent_logs: deque[dict] = deque(maxlen=100)


def _write_csv(path: str, row: Dict[str, Any]) -> None:
    """단일 로그를 CSV 파일로 저장한다."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    write_header = not os.path.exists(path)
    with open(path, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=row.keys())
        if write_header:
            writer.writeheader()
        writer.writerow(row)


def log_trade(event_type: str, data: Dict[str, Any], path: str = "logs/trade_history.csv") -> None:
    """이벤트 유형과 데이터를 받아 로그를 남긴다."""
    entry = {"time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "type": event_type}
    entry.update(data)
    _recent_logs.appendleft(entry)
    try:
        _write_csv(path, entry)
    except Exception:
        pass


def get_recent_logs(limit: int = 20) -> list[dict]:
    """최근 ``limit``개 로그를 반환한다."""
    return list(_recent_logs)[:limit]


def log_config_change(
    category: str,
    key: str,
    before: Any,
    after: Any,
    path: str = "logs/config_history.csv",
) -> None:
    """설정 변경 내역을 CSV 로 기록한다."""
    entry = {
        "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "category": category,
        "key": key,
        "before": before,
        "after": after,
    }
    _recent_logs.appendleft(entry)
    try:
        _write_csv(path, entry)
    except Exception:
        pass

