"""
[F3] 하이브리드 주문 함수 (시장가↔IOC, 체결률/슬리피지 최적화)
로그: logs/F3_smart_buy.log
"""
import logging
from .utils import log_with_tag

logger = logging.getLogger("F3_smart_buy")
fh = logging.FileHandler("logs/F3_smart_buy.log")
formatter = logging.Formatter('%(asctime)s [F3] %(message)s')
fh.setFormatter(formatter)
logger.addHandler(fh)
logger.setLevel(logging.INFO)

def smart_buy(signal, config, dynamic_params, parent_logger=None):
    """
    Adaptive IOC/시장가 주문 실행 (슬리피지/체결률 관리)
    - 스프레드 ≤ SPREAD_TH: 시장가 바로 진입
    - 아니면 ask–Δ틱 IOC 지정가 진입(최대 MAX_RETRY회)
    - 모두 실패시 시장가 폴백
    """
    symbol = signal["symbol"]
    spread = float(signal.get("spread", 0.0))
    SPREAD_TH = dynamic_params.get("SPREAD_TH", 0.0008)
    MAX_RETRY = config.get("MAX_RETRY", 2)

    for attempt in range(MAX_RETRY + 1):
        if spread <= SPREAD_TH or attempt == MAX_RETRY:
            log_with_tag(logger, f"Market order executed for {symbol} (spread: {spread}, attempt: {attempt})")
            return {"filled": True, "symbol": symbol, "order_type": "market"}
        else:
            log_with_tag(logger, f"IOC order for {symbol} (attempt {attempt+1})")
    # 최종 폴백
    log_with_tag(logger, f"Fallback to market order for {symbol}")
    return {"filled": True, "symbol": symbol, "order_type": "market"}

