"""
UPBIT 5분봉 자동매매 메인 트레이더
초보자용 상세 주석 포함 (2025)
"""
import threading, time
from .strategy import select_strategy
from .indicators import calc_indicators

def run_trader(settings, logger):
    # 봇을 백그라운드에서 구동 (스레드로)
    logger.info("[TRADER] 트레이더 시작")
    while settings['running']:
        try:
            # 실제 5분봉 데이터 수집/전략 평가/주문 실행 로직
            # ...
            time.sleep(5)
        except Exception as e:
            logger.error(f"[TRADER] 예외: {e}")
    logger.info("[TRADER] 트레이더 종료")
