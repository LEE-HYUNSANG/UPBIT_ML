"""
UPBIT 5분봉 자동매매 9대 전략 모듈 (최종)
각 전략별 파라미터/조건/함수, STRATS 등록, select_strategy 지원
초보자도 이해할 수 있는 상세 주석 포함
"""
import logging

logger = logging.getLogger(__name__)

def m_break(df, tis, params):
    """
    M-BREAK (강한 돌파+추세+거래량)
    ema5 > ema20 > ema60, ATR ≥ 0.035,
    20봉 평균 거래량의 1.8배 폭증, 체결강도 120+, 전고점 0.15% 돌파
    """
    logger.cal("m_break evaluation")
    # 최근 1봉 데이터
    last = df.iloc[-1]  # 현재 봉
    # 이전 20봉 동안의 최고가(돌파 기준선)
    prev_high = df['high'][-21:-1].max()
    ok = (
        last['ema5'] > last['ema20'] > last['ema60'] and
        last['atr'] >= params.get('atr', 0.035) and
        last['volume'] >= df['volume'][-20:].mean() * 1.8 and  # 거래량 폭증 여부
        tis >= 120 and                                # 체결강도 120 이상
        last['close'] > prev_high * 1.0015             # 전고 돌파
    )
    logger.cal(
        "m_break close=%s prev_high=%s volume=%s atr=%s tis=%s -> %s",
        last['close'],
        prev_high,
        last['volume'],
        last['atr'],
        tis,
        ok,
    )
    return ok, params

def p_pull(df, tis, params):
    """
    P-PULL (눌림목 반등)
    ema5 > ema20 > ema60, ema50 근접(0.3% 이내), rsi ≤ 28, 거래량 증가
    """
    logger.cal("p_pull evaluation")
    last = df.iloc[-1]  # 현재 봉 데이터
    ema50 = df['ema50'].iloc[-1]
    ok = (
        last['ema5'] > last['ema20'] > last['ema60'] and
        abs(last['close'] - ema50) / (ema50 + 1e-9) < 0.003 and
        last['rsi'] <= params.get('rsi', 28) and
        last['volume'] >= df['volume'].iloc[-2] * 1.2
    )
    logger.cal(
        "p_pull close=%s ema50=%s rsi=%s volume=%s -> %s",
        last['close'],
        ema50,
        last['rsi'],
        last['volume'],
        ok,
    )
    return ok, params

def t_flow(df, tis, params):
    """
    T-FLOW (중기 추세+OBV)
    ema20 기울기 0.15%↑, obv 3봉 연속 상승, rsi 48~60
    """
    logger.cal("t_flow evaluation")
    # EMA20 최근 5봉 기울기 계산
    ema20_slope = (df['ema20'].iloc[-1] - df['ema20'].iloc[-5]) / (abs(df['ema20'].iloc[-5]) + 1e-9)
    # OBV가 3봉 연속 상승하는지 체크
    obv_inc = all(df['obv'].iloc[-i] > df['obv'].iloc[-i-1] for i in range(1, 4))
    rsi = df['rsi'].iloc[-1]
    ok = (
        ema20_slope > 0.0015 and obv_inc and 48 <= rsi <= 60
    )
    logger.cal(
        "t_flow slope=%s obv_inc=%s rsi=%s -> %s",
        ema20_slope,
        obv_inc,
        rsi,
        ok,
    )
    return ok, params

def b_low(df, tis, params):
    """
    B-LOW (박스권 하단 반등)
    80봉 내 박스폭 6% 이내, 저점 터치, rsi < 25
    """
    logger.cal("b_low evaluation")
    # 최근 80봉의 최저·최고가
    low80 = df['low'][-80:].min()
    high80 = df['high'][-80:].max()
    last = df.iloc[-1]
    # 박스폭 비율 계산
    box_ratio = (high80 - low80) / (low80+1e-9)
    ok = (
        box_ratio < 0.06 and
        last['low'] <= low80 * 1.01 and
        last['rsi'] < params.get('rsi', 25)
    )
    logger.cal(
        "b_low box_ratio=%s low80=%s rsi=%s -> %s",
        box_ratio,
        low80,
        last['rsi'],
        ok,
    )
    return ok, params

def v_rev(df, tis, params):
    """
    V-REV (대폭락 후 강한 반등)
    직전봉 -4% 이상 하락, 거래량 2.5배↑, RSI14 18→20 상승, 반등폭 4%↑
    """
    logger.cal("v_rev evaluation")
    last = df.iloc[-1]   # 현재 봉
    prev = df.iloc[-2]   # 직전 봉
    price_drop = (prev['close'] - last['close']) / (prev['close'] + 1e-9)
    volume_burst = last['volume'] > prev['volume'] * 2.5
    rsi_rise = last['rsi'] > 20 and prev['rsi'] <= 18
    price_rebound = (last['close'] - prev['close']) / (prev['close']+1e-9) > 0.04
    ok = (
        price_drop >= 0.04 and
        volume_burst and
        rsi_rise and
        price_rebound
    )
    logger.cal(
        "v_rev drop=%s vol_burst=%s rsi_rise=%s rebound=%s -> %s",
        price_drop,
        volume_burst,
        rsi_rise,
        price_rebound,
        ok,
    )
    return ok, params

def g_rev(df, tis, params):
    """
    G-REV (골든크로스+지지)
    ema50 > ema200 골든, rsi ≥ 48, 거래량 이전봉 대비 0.6배↑
    """
    logger.cal("g_rev evaluation")
    last = df.iloc[-1]  # 현재 봉 데이터
    golden = last['ema50'] > last['ema200']
    ok = (
        golden and
        last['rsi'] >= 48 and
        last['volume'] >= df['volume'].iloc[-2] * 0.6
    )
    logger.cal(
        "g_rev golden=%s rsi=%s volume=%s -> %s",
        golden,
        last['rsi'],
        last['volume'],
        ok,
    )
    return ok, params

def vol_brk(df, tis, params):
    """
    VOL-BRK (ATR 폭발·신고가)
    ATR 비율 급등, 거래량 증가, 신고가 돌파, rsi ≥ 60
    """
    logger.cal("vol_brk evaluation")
    last = df.iloc[-1]  # 현재 봉
    atr10 = df['atr'][-10:].mean()
    vol20 = df['volume'][-20:].mean()     # 20봉 평균 거래량
    high20 = df['high'][-20:].max()       # 20봉 최고가
    ok = (
        last['atr'] > atr10 * 1.5 and
        last['volume'] > vol20 * 2 and
        last['high'] > high20 * 0.999 and
        last['rsi'] >= 60
    )
    logger.cal(
        "vol_brk atr_ratio=%s vol_ratio=%s high=%s rsi=%s -> %s",
        last['atr'] / (atr10 + 1e-9),
        last['volume'] / (vol20+1e-9),
        last['high'],
        last['rsi'],
        ok,
    )
    return ok, params

def ema_stack(df, tis, params):
    """
    EMA-STACK (다중 EMA + ADX)
    ema25 > ema100 > ema200, adx ≥ 30
    """
    logger.cal("ema_stack evaluation")
    last = df.iloc[-1]
    ok = last['ema25'] > last['ema100'] > last['ema200'] and last['adx'] >= 30
    logger.cal(
        "ema_stack adx=%s -> %s",
        last['adx'],
        ok,
    )
    return ok, params

def vwap_bnc(df, tis, params):
    """
    VWAP-BNC (VWAP/RSI 조합)
    ema5 > ema20 > ema60, vwap 근접, rsi 45~60, 거래량 증가
    """
    logger.cal("vwap_bnc evaluation")
    last = df.iloc[-1]       # 현재 봉
    vwap = last['vwap']
    vwap_close_ratio = abs(last['close'] - vwap) / (vwap+1e-9)  # 종가와 VWAP 차이
    ok = (
        last['ema5'] > last['ema20'] > last['ema60'] and
        vwap_close_ratio < 0.012 and
        45 <= last['rsi'] <= 60 and
        last['volume'] >= df['volume'].iloc[-2]
    )
    logger.cal(
        "vwap_bnc vwap_ratio=%s rsi=%s volume=%s -> %s",
        vwap_close_ratio,
        last['rsi'],
        last['volume'],
        ok,
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

# ---------------------------------------------------------------------------
# 자동 등록되지 않은 전략에 대한 기본 함수 생성
# ---------------------------------------------------------------------------
from strategy_loader import load_strategies


def _placeholder(name):
    def func(df, tis, params):
        logger.warning("Strategy %s not implemented", name)
        return False, params
    func.__name__ = name.lower().replace("-", "_")
    return func


_SPECS = load_strategies()
for _sc in _SPECS:
    if _sc not in STRATS:
        STRATS[_sc] = _placeholder(_sc)
        globals()[_sc.lower().replace("-", "_")] = STRATS[_sc]

def select_strategy(strategy_name, df, tis, params):
    """
    전략명/지표/체결강도/파라미터로 전략 함수 실행
    사용 예: ok, param = select_strategy('M-BREAK', df, tis, {...})
    """
    logger.cal("select_strategy %s", strategy_name)
    func = STRATS.get(strategy_name)   # 전략 이름으로 함수 찾기
    if not func:
        return False, {}
    ok, res = func(df, tis, params)
    logger.cal("%s -> %s", strategy_name, ok)
    return ok, res
