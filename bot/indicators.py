"""
기술적 지표 계산 모듈
주요 기능: pandas+ta-lib 기반 지표(EMA, RSI, ATR 등) 계산
초보자용 상세 주석 포함
"""
import pandas as pd
import talib as ta

def calc_indicators(df):
    """
    인풋: df - OHLCV 데이터프레임
    아웃풋: df에 각종 기술적 지표 컬럼을 추가하여 반환
    """
    # EMA(5, 20, 60)
    df['EMA5'] = ta.EMA(df['close'], timeperiod=5)
    df['EMA20'] = ta.EMA(df['close'], timeperiod=20)
    df['EMA60'] = ta.EMA(df['close'], timeperiod=60)
    # RSI(14)
    df['RSI14'] = ta.RSI(df['close'], timeperiod=14)
    # ATR(14)
    df['ATR14'] = ta.ATR(df['high'], df['low'], df['close'], timeperiod=14)
    # 기타 필요한 지표 추가 가능 (MACD, OBV 등)
    # 결측치 보정(맨 앞부분)
    df.fillna(method="bfill", inplace=True)
    return df
