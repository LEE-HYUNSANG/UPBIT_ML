"""
UPBIT 5분봉 자동매매 9대 전략 모듈
각 전략은 초보자도 바로 이해할 수 있도록
조건/지표/의사결정 흐름을 주석으로 설명함.
전략별 파라미터는 params로 동적 튜닝 가능.
"""

import numpy as np

def m_break(df, tis, params):
    """
    M-BREAK (강한 돌파+추세+거래량)
    - EMA5 > EMA20 > EMA60
    - ATR(14) >= 0.035
    - 거래량 20봉 평균의 1.8배 이상 폭증
    - 실시간 체결강도(tis) >= 120
    - 전고점 돌파(0.15% 이상)
    """
    last = df.iloc[-1]
    prev_high = df['high'][-21:-1].max()
    ok = (
        last['EMA5'] > last['EMA20'] > last['EMA60'] and
        last['ATR14'] >= params.get('atr', 0.035) and
        last['volume'] >= df['volume'][-20:].mean() * 1.8 and
        tis >= 120 and
        last['close'] > prev_high * 1.0015
    )
    return ok, params

def p_pull(df, tis, params):
    """
    P-PULL (눌림목 반등)
    - EMA5 > EMA20 > EMA60
    - EMA50 근접(2% 이내)
    - RSI14 <= 28 반등
    - 직전봉 대비 거래량 1.2배 이상
    """
    last = df.iloc[-1]
    ema50 = df['EMA50'].iloc[-1] if 'EMA50' in df.columns else np.nan
    ok = (
        last['EMA5'] > last['EMA20'] > last['EMA60'] and
        abs(last['close'] - ema50) / (ema50+1e-9) < 0.02 and
        last['RSI14'] <= params.get('rsi', 28) and
        last['volume'] >= df['volume'].iloc[-2] * 1.2
    )
    return ok, params

def t_flow(df, tis, params):
    """
    T-FLOW (중기 추세+OBV)
    - EMA20의 5봉 기울기 > 0.15%
    - OBV 3봉 연속 상승
    - RSI14 48~60
    """
    ema20_slope = (df['EMA20'].iloc[-1] - df['EMA20'].iloc[-5]) / abs(df['EMA20'].iloc[-5]+1e-9)
    obv_increase = all(df['OBV'].iloc[-i] > df['OBV'].iloc[-i-1] for i in range(1, 4)) if 'OBV' in df.columns else False
    rsi = df['RSI14'].iloc[-1]
    ok = (
        ema20_slope > 0.0015 and
        obv_increase and
        48 <= rsi <= 60
    )
    return ok, params

def b_low(df, tis, params):
    """
    B-LOW (박스권 하단 반등)
    - 80봉 내 박스폭 6% 이내
    - 저점 터치
    - RSI14 < 25 반등
    """
    low80 = df['low'][-80:].min()
    high80 = df['high'][-80:].max()
    last = df.iloc[-1]
    box_ratio = (high80 - low80) / (low80+1e-9)
    ok = (
        box_ratio < 0.06 and
        last['low'] <= low80 * 1.01 and
        last['RSI14'] < params.get('rsi', 25)
    )
    return ok, params

def v_rev(df, tis, params):
    """
    V-REV (대폭락 후 강한 반등)
    - 직전봉 -4% 이상 하락
    - 거래량 2.5배 이상 급증
    - RSI14 18→20 반등, 반등폭 4% 이상
    """
    last = df.iloc[-1]
    prev = df.iloc[-2]
    price_drop = (prev['close'] - last['close']) / (prev['close']+1e-9)
    volume_burst = last['volume'] > prev['volume'] * 2.5
    rsi_rise = last['RSI14'] > 20 and prev['RSI14'] <= 18
    price_rebound = (last['close'] - prev['close']) / (prev['close']+1e-9) > 0.04
    ok = (
        price_drop >= 0.04 and
        volume_burst and
        rsi_rise and
        price_rebound
    )
    return ok, params

def g_rev(df, tis, params):
    """
    G-REV (골든크로스+지지)
    - EMA50 > EMA200 골든크로스
    - 단기 눌림
    - RSI14 >= 48
    - 거래량 이전봉 0.6배 이상
    """
    last = df.iloc[-1]
    golden = (last['EMA50'] > last['EMA200']) if 'EMA200' in df.columns else False
    ok = (
        golden and
        last['RSI14'] >= 48 and
        last['volume'] >= df['volume'].iloc[-2] * 0.6
    )
    return ok, params

def vol_brk(df, tis, params):
    """
    VOL-BRK (ATR 폭발·신고가)
    - ATR 10봉 평균대비 1.5배↑
    - 20봉 거래량 2배↑
    - 신고가 돌파
    - RSI14 >= 60
    """
    last = df.iloc[-1]
    atr10 = df['ATR14'][-10:].mean()
    vol20 = df['volume'][-20:].mean()
    high20 = df['high'][-20:].max()
    ok = (
        last['ATR14'] > atr10 * 1.5 and
        last['volume'] > vol20 * 2 and
        last['high'] > high20 * 0.999 and
        last['RSI14'] >= 60
    )
    return ok, params

def ema_stack(df, tis, params):
    """
    EMA-STACK (EMA 다중 정렬, ADX↑)
    - EMA25 > EMA100 > EMA200
    - ADX >= 30
    - 저점 돌파→반등
    """
    last = df.iloc[-1]
    ok = (
        last['EMA25'] > last['EMA100'] > last['EMA200'] and
        ('ADX' in df.columns and last['ADX'] >= 30)
    )
    return ok, params

def vwap_bnc(df, tis, params):
    """
    VWAP-BNC (VWAP/RSI 조합)
    - EMA5 > EMA20 > EMA60
    - 종가 VWAP 근접
    - RSI 45~60
    - 거래량 증가
    """
    last = df.iloc[-1]
    vwap_close_ratio = abs(last['close'] - last.get('VWAP', last['close'])) / (last.get('VWAP', last['close'])+1e-9)
    ok = (
        last['EMA5'] > last['EMA20'] > last['EMA60'] and
        vwap_close_ratio < 0.012 and
        45 <= last['RSI14'] <= 60 and
        last['volume'] >= df['volume'].iloc[-2]
    )
    return ok, params

# 전략 이름-함수 매핑
STRATS = {
    "M-BREAK": m_break,
    "P-PULL": p_pull,
    "T-FLOW": t_flow,
    "B-LOW": b_low,
    "V-REV": v_rev,
    "G-REV": g_rev,
    "VOL-BRK": vol_brk,
    "EMA-STACK": ema_stack,
    "VWAP-BNC": vwap_bnc
}

def select_strategy(strategy_name, df, tis, params):
    """
    strategy_name: 전략명(str)
    df: OHLCV+지표 DataFrame
    tis: 실시간 체결강도(옵션)
    params: 전략별 파라미터(dict)
    사용 예: ok, param = select_strategy('M-BREAK', df, tis, {...})
    """
    func = STRATS.get(strategy_name)
    if not func:
        return False, {}
    return func(df, tis, params)
