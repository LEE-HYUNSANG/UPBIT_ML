import pandas as pd
import numpy as np


def calc_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """Backward compatible wrapper for :func:`compute_indicators`.

    기존 코드에서 ``calc_indicators`` 함수를 사용하던 부분을 그대로 지원하기
    위해 추가된 얇은 래퍼 함수다. 내부적으로 :func:`compute_indicators` 를 호출해
    동일한 결과를 반환한다.
    """
    return compute_indicators(df)

def compute_indicators(df):
    """
    Compute all indicators and derived fields required by strategy formulas.
    Assumes df has at least 'Open', 'High', 'Low', 'Close', 'Volume', and optionally 'Strength'.
    Returns the DataFrame with new indicator columns added.
    """
    # Ensure DataFrame is sorted in time order
    df = df.copy()
    df = df.reset_index(drop=True)

    # 1. Exponential Moving Averages (EMA)
    df['EMA5'] = df['Close'].ewm(span=5, adjust=False).mean()
    df['EMA20'] = df['Close'].ewm(span=20, adjust=False).mean()
    df['EMA60'] = df['Close'].ewm(span=60, adjust=False).mean()
    df['EMA120'] = df['Close'].ewm(span=120, adjust=False).mean()

    # 2. ATR (Average True Range) with period 14
    high_low = df['High'] - df['Low']
    high_close_prev = np.abs(df['High'] - df['Close'].shift(1))
    low_close_prev = np.abs(df['Low'] - df['Close'].shift(1))
    # True Range
    tr = np.maximum.reduce([high_low, high_close_prev, low_close_prev])
    # ATR using Wilder's smoothing (EMA with alpha=1/14)
    df['ATR14'] = tr.ewm(alpha=1/14, adjust=False).mean()
    # Simple moving average of ATR over 20 periods (for squeeze conditions)
    df['ATR14_MA20'] = df['ATR14'].rolling(window=20).mean()

    # 3. RSI (Relative Strength Index)
    # We implement RSI for 14-period. If needed for other periods, adjust accordingly.
    delta = df['Close'].diff()
    up = delta.clip(lower=0)
    down = -delta.clip(upper=0)
    # Wilder's smoothing for average gains and losses
    avg_gain = up.ewm(alpha=1/14, adjust=False).mean()
    avg_loss = down.ewm(alpha=1/14, adjust=False).mean()
    rs = avg_gain / avg_loss
    df['RSI14'] = 100 - (100 / (1 + rs))
    # (If RSI(2) or others needed, similar calculation with period=2, etc.)

    # 4. Moving average of Volume (20-period by default)
    df['Vol_MA20'] = df['Volume'].rolling(window=20).mean()
    # We can similarly compute shorter volume averages if needed (like 5).
    df['Vol_MA5'] = df['Volume'].rolling(window=5).mean()

    # 5. MFI(Money Flow Index)와 VWAP 계산
    tp = (df['High'] + df['Low'] + df['Close']) / 3
    raw_mf = tp * df['Volume']
    pos_mf = raw_mf.where(tp > tp.shift(1), 0.0)
    neg_mf = raw_mf.where(tp < tp.shift(1), 0.0)
    mf_ratio = pos_mf.rolling(window=14).sum() / (neg_mf.rolling(window=14).sum() + 1e-9)
    df['MFI14'] = 100 - (100 / (1 + mf_ratio))

    vwap_num = (tp * df['Volume']).cumsum()
    vwap_den = df['Volume'].cumsum()
    df['VWAP'] = vwap_num / vwap_den

    # 5. Bollinger Bands (20-period, 2 std)
    period = 20
    std = 2
    df['BB_mid'] = df['Close'].rolling(window=period).mean()
    df['BB_std'] = df['Close'].rolling(window=period).std()
    df['BB_upper'] = df['BB_mid'] + std * df['BB_std']
    df['BB_lower'] = df['BB_mid'] - std * df['BB_std']
    # Bollinger Band Width (difference between bands)
    df['BandWidth20'] = df['BB_upper'] - df['BB_lower']
    # Precompute rolling minima for BandWidth20 for strategy formulas
    df['BandWidth20_min10'] = df['BandWidth20'].rolling(window=10).min()
    df['BandWidth20_min20'] = df['BandWidth20'].rolling(window=20).min()

    # 6. Rolling max/min for various look-back periods
    df['MaxHigh5'] = df['High'].rolling(window=5).max()
    df['MinLow5'] = df['Low'].rolling(window=5).min()
    df['MaxHigh10'] = df['High'].rolling(window=10).max()
    df['MinLow10'] = df['Low'].rolling(window=10).min()
    df['MaxHigh20'] = df['High'].rolling(window=20).max()
    df['MinLow20'] = df['Low'].rolling(window=20).min()
    df['MaxHigh60'] = df['High'].rolling(window=60).max()
    df['MinLow60'] = df['Low'].rolling(window=60).min()
    df['MaxHigh120'] = df['High'].rolling(window=120).max()
    df['MinLow120'] = df['Low'].rolling(window=120).min()

    # 7. CCI (Commodity Channel Index, typically 20-period)
    tp = (df['High'] + df['Low'] + df['Close']) / 3  # typical price
    tp_ma = tp.rolling(window=20).mean()
    mad = tp.rolling(window=20).apply(lambda x: np.mean(np.abs(x - np.mean(x))), raw=True)  # mean absolute deviation
    df['CCI20'] = (tp - tp_ma) / (0.015 * mad)

    # 8. Stochastic Oscillator (14,3). Compute Fast %K (14) and Slow %D (3).
    low14 = df['Low'].rolling(window=14).min()
    high14 = df['High'].rolling(window=14).max()
    stoch_k = (df['Close'] - low14) / (high14 - low14) * 100
    df['StochK14'] = stoch_k
    df['StochD14'] = stoch_k.rolling(window=3).mean()  # 3-period SMA of %K

    # 9. MACD (Moving Average Convergence Divergence, 12,26 with signal 9)
    ema12 = df['Close'].ewm(span=12, adjust=False).mean()
    ema26 = df['Close'].ewm(span=26, adjust=False).mean()
    df['MACD_line'] = ema12 - ema26
    df['MACD_signal'] = df['MACD_line'].ewm(span=9, adjust=False).mean()
    df['MACD_hist'] = df['MACD_line'] - df['MACD_signal']

    # 10. ADX and DIs (14-period)
    # Compute directional movements
    plus_dm = df['High'].diff()
    minus_dm = -df['Low'].diff()
    plus_dm[plus_dm < 0] = 0
    minus_dm[minus_dm < 0] = 0
    minus_dm[df['High'].diff() > df['Low'].diff()] = 0
    plus_dm[df['Low'].diff() > df['High'].diff()] = 0
    # Smooth DM and TR with Wilder's method
    plus_dm14 = plus_dm.ewm(alpha=1/14, adjust=False).mean()
    minus_dm14 = minus_dm.ewm(alpha=1/14, adjust=False).mean()
    # Reuse ATR14 (already Wilder smoothed) for TR14
    tr14 = df['ATR14']
    # Compute DI and DX
    df['DI_plus'] = 100 * plus_dm14 / tr14
    df['DI_minus'] = 100 * minus_dm14 / tr14
    dx = 100 * np.abs(df['DI_plus'] - df['DI_minus']) / (df['DI_plus'] + df['DI_minus'])
    df['ADX14'] = dx.ewm(alpha=1/14, adjust=False).mean()

    # 11. Parabolic SAR (using default acceleration=0.02, max=0.2)
    # We'll compute PSAR iteratively
    psar = [np.nan] * len(df)
    trend_up = True  # initial trend guess
    # Initialize first PSAR
    psar[0] = df['Low'].iloc[0]  # start from first low (if assuming uptrend, else use high for downtrend)
    ep = df['High'].iloc[0]  # extreme point
    accel = 0.02
    for i in range(1, len(df)):
        # Calculate PSAR for i
        prev_psar = psar[i-1]
        # Update extreme point and trend
        if trend_up:
            # If uptrend continues
            psar[i] = prev_psar + accel * (ep - prev_psar)
            # Ensure PSAR is not above last two lows
            if psar[i] > df['Low'].iloc[i-1]:
                psar[i] = df['Low'].iloc[i-1]
            if i > 1 and psar[i] > df['Low'].iloc[i-2]:
                psar[i] = df['Low'].iloc[i-2]
            # Check for trend reversal
            if df['Low'].iloc[i] < psar[i]:
                trend_up = False
                psar[i] = ep  # next PSAR starts at last EP
                ep = df['Low'].iloc[i]  # reset extreme point
                accel = 0.02  # reset acceleration
            else:
                # No reversal, update EP and accel if new high
                if df['High'].iloc[i] > ep:
                    ep = df['High'].iloc[i]
                    accel = min(accel + 0.02, 0.2)
        else:
            # Downtrend case
            psar[i] = prev_psar + accel * (ep - prev_psar)
            # Ensure PSAR not below last two highs
            if psar[i] < df['High'].iloc[i-1]:
                psar[i] = df['High'].iloc[i-1]
            if i > 1 and psar[i] < df['High'].iloc[i-2]:
                psar[i] = df['High'].iloc[i-2]
            # Check for trend reversal
            if df['High'].iloc[i] > psar[i]:
                trend_up = True
                psar[i] = ep
                ep = df['High'].iloc[i]
                accel = 0.02
            else:
                if df['Low'].iloc[i] < ep:
                    ep = df['Low'].iloc[i]
                    accel = min(accel + 0.02, 0.2)
    df['PSAR'] = psar

    # 12. Ichimoku Components
    # Tenkan-sen (Conversion line, 9-period midpoint)
    df['Tenkan9'] = (df['High'].rolling(window=9).max() + df['Low'].rolling(window=9).min()) / 2
    # Kijun-sen (Base line, 26-period midpoint)
    df['Kijun26'] = (df['High'].rolling(window=26).max() + df['Low'].rolling(window=26).min()) / 2
    # Senkou Span A (Leading Span A, average of Tenkan and Kijun, plotted 26 forward)
    spanA_raw = ((df['Tenkan9'] + df['Kijun26']) / 2)
    df['SpanA'] = spanA_raw.shift(26)  # shift into future position
    # Senkou Span B (Leading Span B, 52-period midpoint, plotted 26 forward)
    spanB_raw = (df['High'].rolling(window=52).max() + df['Low'].rolling(window=52).min()) / 2
    df['SpanB'] = spanB_raw.shift(26)
    # 가장 강한 구름 값을 구하기 위한 MaxSpan 컬럼 추가
    df['MaxSpan'] = np.maximum(df['SpanA'], df['SpanB'])
    # Chikou (Lagging span, close plotted 26 periods back)
    df['LaggingSpan'] = df['Close'].shift(-26)

    # Fill initial NaNs if needed (though it’s expected to have NaNs for initial periods due to calculations)
    # Typically, for trading usage, one would start signals after these NaNs.
    return df
