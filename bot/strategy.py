"""
UPBIT 5분봉 자동매매 9대 전략 모듈 (최종)
각 전략별 파라미터/조건/함수, STRATS 등록, select_strategy 지원
초보자도 이해할 수 있는 상세 주석 포함
"""
import numpy as np

def m_break(df, tis, params):
    """
    M-BREAK (강한 돌파+추세+거래량)
    EMA5 > EMA20 > EMA60, ATR14 ≥ 0.035,
    20봉 평균 거래량의 1.8배 폭증, 체결강도 120+, 전고점 0.15% 돌파
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
    EMA5 > EMA20 > EMA60, EMA50 근접(2% 이내), RSI14 ≤ 28, 직전봉 대비 거래량 1.2배 이상
    """
    last = df.iloc[-1]
    ema50 = df['EMA50'].iloc[-1]
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
    EMA20 5봉 기울기 > 0.15%, OBV 3봉 연속 상승, RSI14 48~60
    """
    ema20_slope = (df['EMA20'].iloc[-1] - df['EMA20'].iloc[-5]) / (abs(df['EMA20'].iloc[-5])+1e-9)
    obv_inc = all(df['OBV'].iloc[-i] > df['OBV'].iloc[-i-1] for i in range(1, 4))
    rsi = df['RSI14'].iloc[-1]
    ok = (
        ema20_slope > 0.0015 and
        obv_inc and
        48 <= rsi <= 60
    )
    return ok, params

def b_low(df, tis, params):
    """
    B-LOW (박스권 하단 반등)
    80봉 내 박스폭 6% 이내, 저점 터치, RSI14 < 25
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
    직전봉 -4% 이상 하락, 거래량 2.5배↑, RSI14 18→20 상승, 반등폭 4%↑
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
    EMA50 > EMA200 골든, RSI14 ≥ 48, 거래량 이전봉 0.6배↑
    """
    last = df.iloc[-1]
    golden = (last['EMA50'] > last['EMA200'])
    ok = (
        golden and
        last['RSI14'] >= 48 and
        last['volume'] >= df['volume'].iloc[-2] * 0.6
    )
    return ok, params

def vol_brk(df, tis, params):
    """
    VOL-BRK (ATR 폭발·신고가)
    ATR14 10봉 평균의 1.5배↑, 20봉 거래량 2배↑, 신고가, RSI14 ≥ 60
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
    EMA-STACK (EMA 다중정렬, ADX↑)
    EMA25 > EMA100 > EMA200, ADX ≥ 30
    """
    last = df.iloc[-1]
    ok = (
        last['EMA25'] > last['EMA100'] > last['EMA200'] and
        last['ADX'] >= 30
    )
    return ok, params

def vwap_bnc(df, tis, params):
    """
    VWAP-BNC (VWAP/RSI 조합)
    EMA5 > EMA20 > EMA60, VWAP 근접, RSI 45~60, 거래량 증가
    """
    last = df.iloc[-1]
    vwap = last['VWAP']
    vwap_close_ratio = abs(last['close'] - vwap) / (vwap+1e-9)
    ok = (
        last['EMA5'] > last['EMA20'] > last['EMA60'] and
        vwap_close_ratio < 0.012 and
        45 <= last['RSI14'] <= 60 and
        last['volume'] >= df['volume'].iloc[-2]
    )
    return ok, params

# 전략명-함수 연결
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
    전략명/지표/체결강도/파라미터로 전략 함수 실행
    사용 예: ok, param = select_strategy('M-BREAK', df, tis, {...})
    """
    func = STRATS.get(strategy_name)
    if not func:
        return False, {}
    return func(df, tis, params)
