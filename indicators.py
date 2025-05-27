import pandas as pd
import numpy as np

def ema(series: pd.Series, period: int) -> pd.Series:
    """
    Calculate Exponential Moving Average (EMA) for the given period.
    """
    return series.ewm(span=period, adjust=False).mean()

def sma(series: pd.Series, period: int) -> pd.Series:
    """
    Calculate Simple Moving Average (SMA) for the given period.
    """
    return series.rolling(window=period, min_periods=period).mean()

def rsi(series: pd.Series, period: int = 14) -> pd.Series:
    """
    Calculate Relative Strength Index (RSI) for the given period.
    Uses the standard Wilder's smoothing method.
    """
    delta = series.diff()
    # Separate positive and negative gains
    up = delta.clip(lower=0)
    down = -delta.clip(upper=0)
    # Calculate exponential moving averages of gains
    avg_gain = up.ewm(alpha=1/period, adjust=False).mean()
    avg_loss = down.ewm(alpha=1/period, adjust=False).mean()
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

def atr(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
    """
    Calculate Average True Range (ATR) for the given period.
    Uses Wilder's smoothing (exponential with alpha=1/period).
    """
    # True range components
    prev_close = close.shift(1)
    tr1 = high - low
    tr2 = (high - prev_close).abs()
    tr3 = (low - prev_close).abs()
    true_range = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    # Wilder's smoothing for ATR
    atr = true_range.ewm(alpha=1/period, adjust=False).mean()
    return atr

def macd(series: pd.Series, fast_period: int = 12, slow_period: int = 26, signal_period: int = 9):
    """
    Calculate MACD (Moving Average Convergence/Divergence) indicator.
    Returns a tuple of (MACD_line, Signal_line, Histogram).
    MACD_line = EMA(fast) - EMA(slow), Signal_line = EMA(MACD_line, signal_period), Histogram = MACD_line - Signal_line.
    """
    ema_fast = ema(series, fast_period)
    ema_slow = ema(series, slow_period)
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal_period, adjust=False).mean()
    hist = macd_line - signal_line
    return macd_line, signal_line, hist

def stochastic(high: pd.Series, low: pd.Series, close: pd.Series, k_period: int = 14, d_period: int = 3, smooth_period: int = 3):
    """
    Calculate Stochastic Oscillator (%K and %D).
    %K = (Close - LowestLow(k_period)) / (HighestHigh(k_period) - LowestLow(k_period)) * 100.
    %D = SMA(%K, d_period) [after applying smoothing to %K if smooth_period > 1].
    Returns a tuple of (stoch_k, stoch_d).
    """
    # Lowest low and highest high over the look-back period
    lowest_low = low.rolling(window=k_period, min_periods=k_period).min()
    highest_high = high.rolling(window=k_period, min_periods=k_period).max()
    # %K calculation
    stoch_k = (close - lowest_low) / (highest_high - lowest_low) * 100
    # Smooth %K if needed (smooth_period usually 3 for Slow Stochastic)
    if smooth_period and smooth_period > 1:
        stoch_k = stoch_k.rolling(window=smooth_period, min_periods=smooth_period).mean()
    # %D is simple moving average of %K over d_period
    stoch_d = stoch_k.rolling(window=d_period, min_periods=d_period).mean()
    return stoch_k, stoch_d

def bollinger_bands(series: pd.Series, period: int = 20, stddev: float = 2):
    """
    Calculate Bollinger Bands for the given period and standard deviation multiplier.
    Returns a tuple of (middle_band, upper_band, lower_band).
    middle_band = SMA(period), upper_band = middle_band + stddev*std(period), lower_band = middle_band - stddev*std(period).
    """
    mid = sma(series, period)
    std = series.rolling(window=period, min_periods=period).std(ddof=0)
    upper = mid + stddev * std
    lower = mid - stddev * std
    return mid, upper, lower

def vwap(high: pd.Series, low: pd.Series, close: pd.Series, volume: pd.Series) -> pd.Series:
    """
    Calculate Volume-Weighted Average Price (VWAP).
    This computes intraday VWAP, resetting at each new day (based on date of timestamp).
    Uses typical price ((H+L+C)/3) weighted by volume.
    """
    # Ensure timestamp index or separate date series to group by day
    # Here assume the index or a 'date' column indicates day boundaries
    # Compute typical price
    typical_price = (high + low + close) / 3.0
    # Group cumulative sums by date (assuming index is datetime)
    if hasattr(close.index, 'tz') or isinstance(close.index, pd.DatetimeIndex):
        day_index = close.index.date
    else:
        # If timestamp is a column rather than index
        # Convert timestamps to datetime if not already
        dates = pd.to_datetime(close.index if close.index.dtype != 'datetime64[ns]' else close.index)
        day_index = dates.date
    # Compute cumulative sum of volume and vol*price for each day
    cum_vol = volume.groupby(day_index).cumsum()
    cum_vol_price = (typical_price * volume).groupby(day_index).cumsum()
    vwap_series = cum_vol_price / cum_vol
    return vwap_series

def mfi(high: pd.Series, low: pd.Series, close: pd.Series, volume: pd.Series, period: int = 14) -> pd.Series:
    """
    Calculate Money Flow Index (MFI) for the given period.
    """
    typical_price = (high + low + close) / 3.0
    money_flow = typical_price * volume
    # Determine positive or negative flow direction
    # If today's typical price > yesterday's, it's positive flow, else negative
    tp_diff = typical_price.diff()
    pos_flow = money_flow.where(tp_diff > 0, 0.0)
    neg_flow = money_flow.where(tp_diff < 0, 0.0)
    # Sum flows over the period
    pos_flow_sum = pos_flow.rolling(window=period, min_periods=period).sum()
    neg_flow_sum = neg_flow.rolling(window=period, min_periods=period).sum()
    # Calculate MFI
    money_flow_ratio = pos_flow_sum / neg_flow_sum
    mfi = 100 - (100 / (1 + money_flow_ratio))
    return mfi

def adx(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14):
    """
    Calculate Average Directional Index (ADX) along with +DI and -DI for the given period.
    Returns a tuple of (ADX, DI_plus, DI_minus).
    """
    # Calculate True Range (TR) and directional movements
    prev_high = high.shift(1)
    prev_low = low.shift(1)
    prev_close = close.shift(1)
    # Directional Movements
    up_move = high - prev_high
    down_move = prev_low - low
    plus_dm = up_move.where((up_move > 0) & (up_move > down_move), 0.0)
    minus_dm = down_move.where((down_move > 0) & (down_move > up_move), 0.0)
    # True Range
    tr = pd.DataFrame({
        'tr1': high - low,
        'tr2': (high - prev_close).abs(),
        'tr3': (low - prev_close).abs()
    }).max(axis=1)
    # Wilder's smoothing (alpha = 1/period) for TR and DMs
    atr_series = tr.ewm(alpha=1/period, adjust=False).mean()
    plus_dm_smoothed = plus_dm.ewm(alpha=1/period, adjust=False).mean()
    minus_dm_smoothed = minus_dm.ewm(alpha=1/period, adjust=False).mean()
    # Calculate DI+
    plus_di = 100 * (plus_dm_smoothed / atr_series)
    minus_di = 100 * (minus_dm_smoothed / atr_series)
    # Calculate DX and ADX
    dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di)
    adx_series = dx.ewm(alpha=1/period, adjust=False).mean()
    return adx_series, plus_di, minus_di

def ichimoku(high: pd.Series, low: pd.Series, close: pd.Series,
             tenkan_period: int = 9, kijun_period: int = 26, span_b_period: int = 52):
    """
    Calculate Ichimoku Cloud indicator values (Tenkan-sen, Kijun-sen, Senkou Span A, Senkou Span B, and Chikou Span).
    Note: Senkou spans are usually plotted forward in time (displacement), and Chikou (lagging) is plotted backward.
    For signal calculation, we return spans aligned with current index (not shifted).
    Returns a dictionary with keys: 'tenkan', 'kijun', 'span_a', 'span_b', 'chikou'.
    """
    # Tenkan-sen (Conversion line): 9-period high+low midpoint
    tenkan = (high.rolling(window=tenkan_period, min_periods=tenkan_period).max() + 
              low.rolling(window=tenkan_period, min_periods=tenkan_period).min()) / 2.0
    # Kijun-sen (Base line): 26-period high+low midpoint
    kijun = (high.rolling(window=kijun_period, min_periods=kijun_period).max() + 
             low.rolling(window=kijun_period, min_periods=kijun_period).min()) / 2.0
    # Senkou Span A (Leading Span A): (Tenkan + Kijun) / 2, normally shifted 26 ahead
    span_a = (tenkan + kijun) / 2.0
    # Senkou Span B (Leading Span B): 52-period high+low midpoint, normally shifted 26 ahead
    span_b = (high.rolling(window=span_b_period, min_periods=span_b_period).max() + 
              low.rolling(window=span_b_period, min_periods=span_b_period).min()) / 2.0
    # Chikou Span (Lagging Span): close price shifted 26 periods back (here we align by shifting forward to current index)
    chikou = close.shift(periods=-26)
    return {
        'tenkan': tenkan,
        'kijun': kijun,
        'span_a': span_a,
        'span_b': span_b,
        'chikou': chikou
    }

def parabolic_sar(high: pd.Series, low: pd.Series, step: float = 0.02, max_step: float = 0.2) -> pd.Series:
    """
    Calculate Parabolic SAR for the given high/low series.
    Returns a Series of SAR values.
    """
    length = len(high)
    sar = pd.Series(index=high.index, dtype=float)
    # Initialize trend direction and extreme points
    if length == 0:
        return sar
    # Start with initial trend based on first two bars
    sar.iloc[0] = low.iloc[0]  # starting SAR (could also use first close or such)
    up_trend = True
    # Set initial extreme points
    ep = high.iloc[0]  # extreme price for up trend
    af = step  # acceleration factor
    for i in range(1, length):
        prev_sar = sar.iloc[i-1]
        # Update SAR
        sar_val = prev_sar + af * (ep - prev_sar)
        # Ensure SAR is within last two bars' range to avoid premature flip
        if up_trend:
            sar_val = min(sar_val, low.iloc[i-1], low.iloc[i])
        else:
            sar_val = max(sar_val, high.iloc[i-1], high.iloc[i])
        # Determine trend reversal
        if up_trend:
            if low.iloc[i] < sar_val:  # downtrend starts
                up_trend = False
                sar_val = ep  # SAR resets to prior EP
                ep = low.iloc[i]  # new extreme point for downtrend
                af = step  # reset acceleration factor
            else:
                # Continue uptrend
                if high.iloc[i] > ep:
                    ep = high.iloc[i]
                    af = min(af + step, max_step)
        else:  # currently in downtrend
            if high.iloc[i] > sar_val:  # uptrend starts
                up_trend = True
                sar_val = ep
                ep = high.iloc[i]
                af = step
            else:
                # Continue downtrend
                if low.iloc[i] < ep:
                    ep = low.iloc[i]
                    af = min(af + step, max_step)
        sar.iloc[i] = sar_val
    return sar


def calc_buy_sell_qty_5m(trades: pd.DataFrame, window: str = "5min") -> pd.DataFrame:
    """Calculate rolling 5 minute buy/sell quantities.

    Parameters
    ----------
    trades : pandas.DataFrame
        Trade data with ``trade_volume`` and ``is_buyer_maker`` columns and a
        ``DatetimeIndex``.
    window : str, default "5min"
        Rolling aggregation window.  The default computes 5 minute sums.

    Returns
    -------
    pandas.DataFrame
        Original ``trades`` with ``BuyQty_5m`` and ``SellQty_5m`` columns
        added representing the cumulative buy and sell quantities over the
        rolling window.
    """

    df = trades.copy()
    df["BuyQty_5m"] = (
        df["trade_volume"].where(df["is_buyer_maker"] == False, 0).rolling(window).sum()
    )
    df["SellQty_5m"] = (
        df["trade_volume"].where(df["is_buyer_maker"] == True, 0).rolling(window).sum()
    )
    return df
