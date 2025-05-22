"""
업비트 5분봉 자동매매용 기술적 지표 계산 (25전략 대응 완전판)
- EMA, MA, RSI, ATR, ADX, OBV, VWAP, MACD, Bollinger Bands, CCI, MFI, Stochastic, Ichimoku 등
- min/max/avg/pullback/bullish_candle/rolling 컬럼 포함
"""
import pandas as pd
import numpy as np
import talib as ta
import logging

logger = logging.getLogger(__name__)

def calc_indicators(df):
    """
    입력: df - OHLCV DataFrame (open/high/low/close/volume)
    출력: df - 25전략 공식에 필요한 모든 컬럼 추가
    """
    # EMA/MA
    for n in [5, 14, 20, 25, 50, 60, 100, 120, 200]:
        df[f'ema{n}'] = ta.EMA(df['close'], n)
        df[f'ma{n}'] = ta.SMA(df['close'], n)
    # RSI
    for n in [2, 5, 14]:
        df[f'rsi{n}'] = ta.RSI(df['close'], n)
    # ATR (진짜 ATR)
    df['atr14'] = ta.ATR(df['high'], df['low'], df['close'], 14)
    # ADX, DI
    df['adx14'] = ta.ADX(df['high'], df['low'], df['close'], 14)
    df['di_plus'] = ta.PLUS_DI(df['high'], df['low'], df['close'], 14)
    df['di_minus'] = ta.MINUS_DI(df['high'], df['low'], df['close'], 14)
    # OBV
    df['obv'] = ta.OBV(df['close'], df['volume'])
    # VWAP
    df['vwap'] = (df['close'] * df['volume']).cumsum() / (df['volume'].cumsum() + 1e-9)
    # MACD
    macd, macd_signal, macd_hist = ta.MACD(df['close'], 12, 26, 9)
    df['macd'] = macd
    df['macd_signal'] = macd_signal
    df['macd_hist'] = macd_hist
    # Bollinger Bands (20,2)
    df['bb_mid202'] = ta.SMA(df['close'], 20)
    df['bb_std202'] = ta.STDDEV(df['close'], 20, 1)
    df['bb_upper202'] = df['bb_mid202'] + 2 * df['bb_std202']
    df['bb_lower202'] = df['bb_mid202'] - 2 * df['bb_std202']
    df['bandwidth20'] = (df['bb_upper202'] - df['bb_lower202']) / (df['bb_mid202'] + 1e-9)
    # MFI
    df['mfi14'] = ta.MFI(df['high'], df['low'], df['close'], df['volume'], 14)
    # CCI
    df['cci20'] = ta.CCI(df['high'], df['low'], df['close'], 20)
    # Stochastic
    stoch_k, stoch_d = ta.STOCH(df['high'], df['low'], df['close'], 14, 3, 0, 3, 0)
    df['stoch_k143'] = stoch_k
    df['stoch_d143'] = stoch_d
    # Ichimoku
    nine_high = df['high'].rolling(window=9).max()
    nine_low = df['low'].rolling(window=9).min()
    df['tenkan9'] = (nine_high + nine_low) / 2
    twenty_six_high = df['high'].rolling(window=26).max()
    twenty_six_low = df['low'].rolling(window=26).min()
    df['kijun26'] = (twenty_six_high + twenty_six_low) / 2
    df['senkou_span_a'] = ((df['tenkan9'] + df['kijun26']) / 2).shift(26)
    fifty_two_high = df['high'].rolling(window=52).max()
    fifty_two_low = df['low'].rolling(window=52).min()
    df['senkou_span_b'] = ((fifty_two_high + fifty_two_low) / 2).shift(26)
    # min/max/avg/rolling 필드
    df['maxhigh20'] = df['high'].rolling(window=20).max()
    df['minlow5'] = df['low'].rolling(window=5).min()
    df['minlow10'] = df['low'].rolling(window=10).min()
    df['minlow20'] = df['low'].rolling(window=20).min()
    df['ma_vol20'] = df['volume'].rolling(window=20).mean()
    df['cumvol_today'] = df['volume'].expanding().sum()
    df['prevclose'] = df['close'].shift(1)
    # 캔들/파생 필드
    df['bullish_candle'] = (df['close'] > df['open']).astype(int)
    df['bearish_candle'] = (df['close'] < df['open']).astype(int)
    df['pullback'] = (df['high'] - df['close']) / (df['high'] + 1e-9)
    # 결측값 보정
    df.bfill(inplace=True)
    df.fillna(0, inplace=True)
    if not df.empty:
        logger.info("Indicators calculated: %s", df.iloc[-1].to_dict())
    return df
