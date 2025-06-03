"""
F4 risk_utils - 공용 유틸, 상태 정의, 타임스탬프 등
"""
from enum import Enum
from common_utils import now

class RiskState(Enum):
    ACTIVE = 1
    PAUSE = 2
    DISABLE = 3
    HALT = 4

