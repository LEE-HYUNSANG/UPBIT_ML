"""
기술적 지표 계산 모듈 (ta-lib + pandas)
EMA, RSI, ATR, ADX, OBV, VWAP 등 9전략에서 필요한 지표 전체 포함
"""
import pandas as pd  # 데이터프레임 처리를 위해 사용
import numpy as np   # 수치 계산용
import talib as ta   # TA-Lib: 기술적 지표 계산 라이브러리

def calc_indicators(df):
    """
    입력: df - OHLCV 데이터프레임 (컬럼명: open/high/low/close/volume)
    출력: df - 지표 컬럼 추가 후 반환
    """
    # 이동평균선(EMA) 계산
    df['EMA5'] = ta.EMA(df['close'], 5)    # 5봉 EMA
    df['EMA20'] = ta.EMA(df['close'], 20)   # 20봉 EMA
    df['EMA25'] = ta.EMA(df['close'], 25)
    df['EMA50'] = ta.EMA(df['close'], 50)   # 50봉 EMA
    df['EMA60'] = ta.EMA(df['close'], 60)   # 60봉 EMA
    df['EMA100'] = ta.EMA(df['close'], 100) # 100봉 EMA
    df['EMA200'] = ta.EMA(df['close'], 200) # 200봉 EMA
    # RSI (14) 계산
    df['RSI14'] = ta.RSI(df['close'], 14)
    # ATR (14) 계산 - 변동성 지표
    df['ATR14'] = ta.ATR(df['high'], df['low'], df['close'], 14)
    # ADX (14) 계산 - 추세 강도
    df['ADX'] = ta.ADX(df['high'], df['low'], df['close'], 14)
    # OBV 지표 - 거래량 흐름
    df['OBV'] = ta.OBV(df['close'], df['volume'])
    # VWAP 계산 (간단 버전, 시가 사용 안 함)
    vwap = (df['close'] * df['volume']).cumsum() / (df['volume'].cumsum() + 1e-9)
    df['VWAP'] = vwap
    # 계산 후 결측값(backfill) 보정 및 0 채우기
    df.fillna(method="bfill", inplace=True)
    df.fillna(0, inplace=True)
    return df  # 지표가 추가된 데이터프레임 반환
