"""
F4 risk_utils - 공용 유틸, 상태 정의, 타임스탬프 등
"""
import time
from enum import Enum

class RiskState(Enum):
    ACTIVE = 1
    PAUSE = 2
    DISABLE = 3
    HALT = 4

def now() -> float:
    """Return current epoch timestamp in seconds as a float."""
    return time.time()
