import pandas as pd
import numpy as np

def ema(series: pd.Series, period: int) -> pd.Series:
    """주어진 기간의 지수 이동 평균(EMA)을 계산합니다."""
    return series.ewm(span=period, adjust=False).mean()

def sma(series: pd.Series, period: int) -> pd.Series:
    """주어진 기간의 단순 이동 평균(SMA)을 계산합니다."""
    return series.rolling(window=period, min_periods=period).mean()

def rsi(series: pd.Series, period: int = 14) -> pd.Series:
    """주어진 기간의 RSI 지표를 계산합니다(Wilder 방식)."""
    delta = series.diff()
    # 상승과 하락 구분
    up = delta.clip(lower=0)
    down = -delta.clip(upper=0)
    # 평균 상승/하락 계산
    avg_gain = up.ewm(alpha=1/period, adjust=False).mean()
    avg_loss = down.ewm(alpha=1/period, adjust=False).mean()
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

def atr(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
    """주어진 기간의 ATR(평균 진폭)을 계산합니다."""
    # 진폭 계산 요소
    prev_close = close.shift(1)
    tr1 = high - low
    tr2 = (high - prev_close).abs()
    tr3 = (low - prev_close).abs()
    true_range = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    # ATR을 위한 Wilder 지수 가중치
    atr = true_range.ewm(alpha=1/period, adjust=False).mean()
    return atr

def macd(series: pd.Series, fast_period: int = 12, slow_period: int = 26, signal_period: int = 9):
    """MACD 지표를 계산하여 (MACD선, 신호선, 히스토그램)을 반환합니다."""
    ema_fast = ema(series, fast_period)
    ema_slow = ema(series, slow_period)
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal_period, adjust=False).mean()
    hist = macd_line - signal_line
    return macd_line, signal_line, hist

def stochastic(high: pd.Series, low: pd.Series, close: pd.Series, k_period: int = 14, d_period: int = 3, smooth_period: int = 3):
    """스토캐스틱 오실레이터(%K, %D)를 계산합니다."""
    # 주어진 기간의 최저가와 최고가 계산
    lowest_low = low.rolling(window=k_period, min_periods=k_period).min()
    highest_high = high.rolling(window=k_period, min_periods=k_period).max()
    # %K 계산
    stoch_k = (close - lowest_low) / (highest_high - lowest_low) * 100
    # 필요 시 %K 평활화(기본 3)
    if smooth_period and smooth_period > 1:
        stoch_k = stoch_k.rolling(window=smooth_period, min_periods=smooth_period).mean()
    # %D는 %K의 이동 평균
    stoch_d = stoch_k.rolling(window=d_period, min_periods=d_period).mean()
    return stoch_k, stoch_d

def bollinger_bands(series: pd.Series, period: int = 20, stddev: float = 2):
    """볼린저 밴드를 계산하여 (중앙선, 상단선, 하단선)을 반환합니다."""
    mid = sma(series, period)
    std = series.rolling(window=period, min_periods=period).std(ddof=0)
    upper = mid + stddev * std
    lower = mid - stddev * std
    return mid, upper, lower

def vwap(high: pd.Series, low: pd.Series, close: pd.Series, volume: pd.Series) -> pd.Series:
    """거래량 가중 평균가(VWAP)를 계산합니다."""
    # 일자별 그룹화를 위한 인덱스 확인
    # 기본적으로 인덱스나 'date' 컬럼을 사용
    # 기준 가격 계산
    typical_price = (high + low + close) / 3.0
    # 날짜별 누적 합 계산
    if hasattr(close.index, 'tz') or isinstance(close.index, pd.DatetimeIndex):
        day_index = close.index.date
    else:
        # 인덱스가 아닌 컬럼인 경우 날짜 변환
        dates = pd.to_datetime(close.index if close.index.dtype != 'datetime64[ns]' else close.index)
        day_index = dates.date
    # 일별 거래량과 거래금액 누적합 계산
    cum_vol = volume.groupby(day_index).cumsum()
    cum_vol_price = (typical_price * volume).groupby(day_index).cumsum()
    vwap_series = cum_vol_price / cum_vol
    return vwap_series

def mfi(high: pd.Series, low: pd.Series, close: pd.Series, volume: pd.Series, period: int = 14) -> pd.Series:
def mfi(high: pd.Series, low: pd.Series, close: pd.Series, volume: pd.Series, period: int = 14) -> pd.Series:
    """주어진 기간의 MFI(자금 흐름 지수)를 계산합니다."""
    typical_price = (high + low + close) / 3.0
    money_flow = typical_price * volume
    # 매수/매도 흐름 방향 판단
    # 오늘의 기준 가격이 어제보다 높으면 양의 흐름
    tp_diff = typical_price.diff()
    pos_flow = money_flow.where(tp_diff > 0, 0.0)
    neg_flow = money_flow.where(tp_diff < 0, 0.0)
    # 기간 동안의 흐름 합산
    pos_flow_sum = pos_flow.rolling(window=period, min_periods=period).sum()
    neg_flow_sum = neg_flow.rolling(window=period, min_periods=period).sum()
    # MFI 계산
    money_flow_ratio = pos_flow_sum / neg_flow_sum
    mfi = 100 - (100 / (1 + money_flow_ratio))
    return mfi

def adx(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14):
def adx(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14):
    """ADX와 +DI, -DI 값을 계산하여 반환합니다."""
    # TR과 방향성 지표 계산
    prev_high = high.shift(1)
    prev_low = low.shift(1)
    prev_close = close.shift(1)
    # 방향성 이동량 계산
    up_move = high - prev_high
    down_move = prev_low - low
    plus_dm = up_move.where((up_move > 0) & (up_move > down_move), 0.0)
    minus_dm = down_move.where((down_move > 0) & (down_move > up_move), 0.0)
    # 진폭(TR) 계산
    tr = pd.DataFrame({
        'tr1': high - low,
        'tr2': (high - prev_close).abs(),
        'tr3': (low - prev_close).abs()
    }).max(axis=1)
    # Wilder 방식의 지수 이동 평균 적용
    atr_series = tr.ewm(alpha=1/period, adjust=False).mean()
    plus_dm_smoothed = plus_dm.ewm(alpha=1/period, adjust=False).mean()
    minus_dm_smoothed = minus_dm.ewm(alpha=1/period, adjust=False).mean()
    # DI+ 계산
    plus_di = 100 * (plus_dm_smoothed / atr_series)
    minus_di = 100 * (minus_dm_smoothed / atr_series)
    # DX와 ADX 계산
    dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di)
    adx_series = dx.ewm(alpha=1/period, adjust=False).mean()
    return adx_series, plus_di, minus_di

def ichimoku(high: pd.Series, low: pd.Series, close: pd.Series,
             tenkan_period: int = 9, kijun_period: int = 26, span_b_period: int = 52):
def ichimoku(high: pd.Series, low: pd.Series, close: pd.Series,
             tenkan_period: int = 9, kijun_period: int = 26, span_b_period: int = 52):
    """일목균형표 지표를 계산하여 각 선을 딕셔너리로 반환합니다."""
    # 전환선: 9일 최고가와 최저가의 중간값
    tenkan = (high.rolling(window=tenkan_period, min_periods=tenkan_period).max() + 
              low.rolling(window=tenkan_period, min_periods=tenkan_period).min()) / 2.0
    # 기준선: 26일 최고가와 최저가의 중간값
    kijun = (high.rolling(window=kijun_period, min_periods=kijun_period).max() + 
             low.rolling(window=kijun_period, min_periods=kijun_period).min()) / 2.0
    # 선행스팬A: (전환선+기준선)/2, 보통 26일 선행
    span_a = (tenkan + kijun) / 2.0
    # 선행스팬B: 52일 최고가와 최저가의 중간값, 26일 선행
    span_b = (high.rolling(window=span_b_period, min_periods=span_b_period).max() + 
              low.rolling(window=span_b_period, min_periods=span_b_period).min()) / 2.0
    # 후행스팬: 종가를 26일 뒤로 이동(여기서는 인덱스에 맞춤)
    chikou = close.shift(periods=-26)
    return {
        'tenkan': tenkan,
        'kijun': kijun,
        'span_a': span_a,
        'span_b': span_b,
        'chikou': chikou
    }

def parabolic_sar(high: pd.Series, low: pd.Series, step: float = 0.02, max_step: float = 0.2) -> pd.Series:
def parabolic_sar(high: pd.Series, low: pd.Series, step: float = 0.02, max_step: float = 0.2) -> pd.Series:
    """주어진 고가/저가 시리즈로 파라볼릭 SAR을 계산합니다."""
    length = len(high)
    sar = pd.Series(index=high.index, dtype=float)
    # 초기 추세 방향과 극단값 설정
    if length == 0:
        return sar
    # 처음 두 봉을 기준으로 추세 결정
    sar.iloc[0] = low.iloc[0]  # 시작 SAR 값
    up_trend = True
    # 초기 극단값 설정
    ep = high.iloc[0]
    af = step
    for i in range(1, length):
        prev_sar = sar.iloc[i-1]
        # SAR 업데이트
        sar_val = prev_sar + af * (ep - prev_sar)
        # 직전 두 봉 범위 내에 있도록 보정
        if up_trend:
            sar_val = min(sar_val, low.iloc[i-1], low.iloc[i])
        else:
            sar_val = max(sar_val, high.iloc[i-1], high.iloc[i])
        # Determine trend reversal
        if up_trend:
            if low.iloc[i] < sar_val:
                up_trend = False
                sar_val = ep
                ep = low.iloc[i]
                af = step
            else:
                # 상승 추세 지속
                if high.iloc[i] > ep:
                    ep = high.iloc[i]
                    af = min(af + step, max_step)
        else:
            if high.iloc[i] > sar_val:
                up_trend = True
                sar_val = ep
                ep = high.iloc[i]
                af = step
            else:
                # 하락 추세 지속
                if low.iloc[i] < ep:
                    ep = low.iloc[i]
                    af = min(af + step, max_step)
        sar.iloc[i] = sar_val
    return sar


def calc_buy_sell_qty_5m(trades: pd.DataFrame, window: str = "5min") -> pd.DataFrame:
def calc_buy_sell_qty_5m(trades: pd.DataFrame, window: str = "5min") -> pd.DataFrame:
    """최근 5분간 매수/매도 수량을 계산하여 컬럼을 추가합니다."""

    df = trades.copy()
    df["BuyQty_5m"] = (
        df["trade_volume"].where(df["is_buyer_maker"] == False, 0).rolling(window).sum()
    )
    df["SellQty_5m"] = (
        df["trade_volume"].where(df["is_buyer_maker"] == True, 0).rolling(window).sum()
    )
    return df
