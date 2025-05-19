"""
기술적 지표 계산 모듈 (ta-lib + pandas)
EMA, RSI, ATR, ADX, OBV, VWAP 등 9전략에서 필요한 지표 전체 포함
"""
import pandas as pd
import numpy as np
import talib as ta

def calc_indicators(df):
    """
    입력: df - OHLCV 데이터프레임 (컬럼명: open/high/low/close/volume)
    출력: df - 지표 컬럼 추가 후 반환
    """
    # 이동평균선(EMA)
    df['EMA5'] = ta.EMA(df['close'], 5)
    df['EMA20'] = ta.EMA(df['close'], 20)
    df['EMA25'] = ta.EMA(df['close'], 25)
    df['EMA50'] = ta.EMA(df['close'], 50)
    df['EMA60'] = ta.EMA(df['close'], 60)
    df['EMA100'] = ta.EMA(df['close'], 100)
    df['EMA200'] = ta.EMA(df['close'], 200)
    # RSI (14)
    df['RSI14'] = ta.RSI(df['close'], 14)
    # ATR (14)
    df['ATR14'] = ta.ATR(df['high'], df['low'], df['close'], 14)
    # ADX (14)
    df['ADX'] = ta.ADX(df['high'], df['low'], df['close'], 14)
    # OBV
    df['OBV'] = ta.OBV(df['close'], df['volume'])
    # VWAP (간이형, 시가x)
    vwap = (df['close'] * df['volume']).cumsum() / (df['volume'].cumsum() + 1e-9)
    df['VWAP'] = vwap
    # 결측값 보정
    df.fillna(method="bfill", inplace=True)
    df.fillna(0, inplace=True)
    return df
