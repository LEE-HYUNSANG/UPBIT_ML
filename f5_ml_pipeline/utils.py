"""공용 유틸리티 함수 모음."""
from datetime import datetime
from pathlib import Path


def timestamp() -> str:
    """현재 시간을 YYYYMMDDHHMMSS 형식으로 반환."""
    return datetime.now().strftime("%Y%m%d%H%M%S")


def ensure_dir(path: str | Path) -> Path:
    """폴더가 없으면 생성 후 Path 객체 반환."""
    p = Path(path)
    p.mkdir(parents=True, exist_ok=True)
    return p
