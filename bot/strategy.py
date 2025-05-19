"""
여러 매매 전략 함수 (초보자 상세 주석)
"""
def select_strategy(strategy_name, data, params):
    # 전략명에 따라 적절한 전략 함수 호출
    if strategy_name == "M-BREAK":
        return m_break(data, params)
    # ... 기타 전략
    return False, {}

def m_break(data, params):
    # M-BREAK 전략 예시: 5EMA>20EMA>60EMA, ATR>=0.035, 거래량폭발, 전고점돌파
    # 실제 구현은 생략, True/False와 파라미터 반환
    return True, params
