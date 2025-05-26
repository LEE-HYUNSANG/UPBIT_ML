import pandas as pd
import json
import logging
import numpy as np
import os
import re
from indicators import (
    ema,
    sma,
    rsi,
    atr,
    macd,
    stochastic,
    bollinger_bands,
    vwap,
    mfi,
    adx,
    ichimoku,
    parabolic_sar,
)

os.makedirs("log", exist_ok=True)
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [F2] [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(os.path.join("log", "F2_signal_engine.log"), encoding="utf-8"),
    ],
)

# Load common parameters and strategy formulas
with open("config/signal.json", "r", encoding="utf-8") as cfg:
    config = json.load(cfg)
with open("strategies_master_pruned.json", "r", encoding="utf-8") as sf:
    strategies = json.load(sf)

# Load per-strategy ON/OFF and priority settings synchronized with the UI
strategy_settings_path = os.path.join("config", "strategy_settings.json")
if os.path.exists(strategy_settings_path):
    with open(strategy_settings_path, "r", encoding="utf-8") as ssf:
        _settings = json.load(ssf)
else:
    # Default: all strategies on with sequential order
    _settings = [
        {"short_code": s["short_code"], "on": True, "order": i + 1}
        for i, s in enumerate(strategies)
    ]

# Map short_code -> settings
STRATEGY_SETTINGS = {s["short_code"]: s for s in _settings}


def _as_utc(ts):
    """Return a timezone-aware timestamp in UTC."""
    ts = pd.to_datetime(ts)
    if ts.tzinfo is None:
        return ts.tz_localize("UTC")
    return ts.tz_convert("UTC")

def f2_signal(df_1m: pd.DataFrame, df_5m: pd.DataFrame, symbol: str = ""):
    """
    Determine buy/sell signals for a given symbol based on 1-minute and 5-minute data.
    df_1m and df_5m are DataFrames with columns ['timestamp','open','high','low','close','volume'].
    Returns a dictionary with the symbol, boolean flags 'buy_signal' and 'sell_signal',
    and lists of triggered strategies.
    """
    logging.debug(f"[{symbol}] Starting signal calculation")
    # Ensure data is sorted by time in ascending order
    df_1m = df_1m.sort_values(by="timestamp").reset_index(drop=True)
    df_5m = df_5m.sort_values(by="timestamp").reset_index(drop=True)
    df_1m["timestamp"] = pd.to_datetime(df_1m["timestamp"], utc=True)
    df_5m["timestamp"] = pd.to_datetime(df_5m["timestamp"], utc=True)

    # Filter out partial candles close to the current time
    now = pd.Timestamp.utcnow().tz_localize("UTC")
    if not df_1m.empty:
        last_1m_ts = _as_utc(df_1m["timestamp"].iloc[-1])
        if (now - last_1m_ts).total_seconds() < 60:
            logging.info(
                f"[{symbol}] Dropping partial 1m candle at {last_1m_ts}"
            )
            df_1m = df_1m.iloc[:-1]
    if not df_5m.empty:
        last_5m_ts = _as_utc(df_5m["timestamp"].iloc[-1])
        if (now - last_5m_ts).total_seconds() < 300:
            logging.info(
                f"[{symbol}] Dropping partial 5m candle at {last_5m_ts}"
            )
            df_5m = df_5m.iloc[:-1]

    if df_1m.empty or df_5m.empty:
        logging.warning(f"[{symbol}] Insufficient data after filtering partial candles")
        return {
            "symbol": symbol,
            "buy_signal": False,
            "sell_signal": False,
            "buy_triggers": [],
            "sell_triggers": [],
        }
    
    # Compute technical indicators for 1-minute data
    df1 = df_1m.copy()
    # EMAs
    for period in config["EMA"]["periods"]:
        df1[f"EMA_{period}"] = ema(df1["close"], period)
    # RSI
    rsi_period = config["RSI"]["period"]
    df1[f"RSI_{rsi_period}"] = rsi(df1["close"], rsi_period)
    # ATR
    atr_period = config["ATR"]["period"]
    df1[f"ATR_{atr_period}"] = atr(df1["high"], df1["low"], df1["close"], atr_period)
    # Bollinger Bands
    bb_period = config["BollingerBands"]["period"]
    bb_std = config["BollingerBands"]["stddev"]
    bb_mid, bb_upper, bb_lower = bollinger_bands(df1["close"], bb_period, bb_std)
    df1["BB_mid"], df1["BB_upper"], df1["BB_lower"] = bb_mid, bb_upper, bb_lower
    # Bollinger Bandwidth and its 20-bar minimum (for Band squeeze strategy)
    df1["BandWidth20"] = df1["BB_upper"] - df1["BB_lower"]
    df1["BandWidth20_min20"] = df1["BandWidth20"].rolling(window=20, min_periods=20).min()
    # Volume moving average
    vol_ma_period = config["Volume"]["ma_period"]
    df1[f"Vol_MA{vol_ma_period}"] = sma(df1["volume"], vol_ma_period)
    # VWAP (intraday)
    df1["VWAP"] = vwap(df1["high"], df1["low"], df1["close"], df1["volume"])
    # Strength (execution strength approximation)
    # Approximate buy vs sell volume using price movement within candle
    high = df1["high"]
    low = df1["low"]
    close = df1["close"]
    vol = df1["volume"]
    # Avoid division by zero in multiplier if high == low
    range_ = (high - low).replace(0, np.nan)
    multiplier = (2*close - high - low) / range_
    # When range is 0, treat multiplier as 0 (neutral)
    multiplier = multiplier.fillna(0)
    buy_vol = (multiplier + 1) / 2 * vol
    sell_vol = vol - buy_vol
    # Calculate strength as (buy_vol/sell_vol)*100, capping extreme values
    strength = pd.Series(index=df1.index, dtype=float)
    strength[:] = 100  # default
    strength[sell_vol > 1e-8] = (buy_vol[sell_vol > 1e-8] / sell_vol[sell_vol > 1e-8]) * 100
    strength[sell_vol <= 1e-8] = 1000.0  # if no selling volume, set very high strength
    df1["Strength"] = strength
    # MACD
    fast = config["MACD"]["fast_period"]
    slow = config["MACD"]["slow_period"]
    sig = config["MACD"]["signal_period"]
    macd_line, signal_line, hist = macd(df1["close"], fast, slow, sig)
    df1["MACD_line"] = macd_line
    df1["MACD_signal"] = signal_line
    df1["MACD_hist"] = hist
    # MFI
    mfi_period = config["MFI"]["period"]
    df1[f"MFI_{mfi_period}"] = mfi(df1["high"], df1["low"], df1["close"], df1["volume"], mfi_period)
    # Stochastic
    stoch_k_period = config["Stochastic"]["k_period"]
    stoch_d_period = config["Stochastic"]["d_period"]
    stoch_smooth = config["Stochastic"]["smooth_period"]
    stoch_k, stoch_d = stochastic(df1["high"], df1["low"], df1["close"], stoch_k_period, stoch_d_period, stoch_smooth)
    df1[f"StochK_{stoch_k_period}"] = stoch_k
    df1[f"StochD_{stoch_k_period}"] = stoch_d
    # Ichimoku (Tenkan, Kijun, SpanA, SpanB, Chikou)
    ichi_cfg = config["Ichimoku"]
    ichi_vals = ichimoku(df1["high"], df1["low"], df1["close"],
                         tenkan_period=ichi_cfg["tenkan_period"],
                         kijun_period=ichi_cfg["kijun_period"],
                         span_b_period=ichi_cfg["senkou_span_b_period"])
    df1["Tenkan"] = ichi_vals["tenkan"]
    df1["Kijun"] = ichi_vals["kijun"]
    df1["SpanA"] = ichi_vals["span_a"]
    df1["SpanB"] = ichi_vals["span_b"]
    df1["Chikou"] = ichi_vals["chikou"]
    # ADX and DI
    adx_period = config["ADX"]["period"]
    adx_series, di_plus, di_minus = adx(df1["high"], df1["low"], df1["close"], adx_period)
    df1[f"ADX_{adx_period}"] = adx_series
    df1["DI_plus"] = di_plus
    df1["DI_minus"] = di_minus
    # Parabolic SAR
    sar_step = config["SAR"]["step"]
    sar_max = config["SAR"]["max_step"]
    df1["PSAR"] = parabolic_sar(df1["high"], df1["low"], sar_step, sar_max)
    # Rolling max/min for various lookback windows (5,20,60,120) needed in formulas
    for window in [5, 20, 60, 120]:
        if window <= len(df1):
            df1[f"MaxHigh{window}"] = df1["high"].rolling(window=window, min_periods=window).max()
            df1[f"MinLow{window}"] = df1["low"].rolling(window=window, min_periods=window).min()
        else:
            # If not enough data for full window, still define columns (will be NaN for latest if window not reached)
            df1[f"MaxHigh{window}"] = df1["high"].rolling(window=window).max()
            df1[f"MinLow{window}"] = df1["low"].rolling(window=window).min()

    logging.debug(
        f"[{symbol}][F2][1분봉] 지표 계산 - EMA_5: {df1['EMA_5'].iloc[-1]}, EMA_20: {df1['EMA_20'].iloc[-1]}, RSI_14: {df1['RSI_14'].iloc[-1]}, ATR_14: {df1['ATR_14'].iloc[-1]}"
    )
    
    # Compute technical indicators for 5-minute data (similar to 1m, but to save time, compute only needed ones)
    df5 = df_5m.copy()
    df5 = df5.sort_values(by="timestamp").reset_index(drop=True)
    for period in config["EMA"]["periods"]:
        df5[f"EMA_{period}"] = ema(df5["close"], period)
    rsi_period = config["RSI"]["period"]
    df5[f"RSI_{rsi_period}"] = rsi(df5["close"], rsi_period)
    atr_period = config["ATR"]["period"]
    df5[f"ATR_{atr_period}"] = atr(df5["high"], df5["low"], df5["close"], atr_period)
    bb_mid, bb_upper, bb_lower = bollinger_bands(df5["close"], bb_period, bb_std)
    df5["BB_mid"], df5["BB_upper"], df5["BB_lower"] = bb_mid, bb_upper, bb_lower
    df5["BandWidth20"] = df5["BB_upper"] - df5["BB_lower"]
    df5["BandWidth20_min20"] = df5["BandWidth20"].rolling(window=20, min_periods=20).min()
    df5[f"Vol_MA{vol_ma_period}"] = sma(df5["volume"], vol_ma_period)
    df5["VWAP"] = vwap(df5["high"], df5["low"], df5["close"], df5["volume"])
    # Strength for 5m (approx same method)
    high5 = df5["high"]; low5 = df5["low"]; close5 = df5["close"]; vol5 = df5["volume"]
    range5 = (high5 - low5).replace(0, np.nan)
    multiplier5 = (2*close5 - high5 - low5) / range5
    multiplier5 = multiplier5.fillna(0)
    buy_vol5 = (multiplier5 + 1) / 2 * vol5
    sell_vol5 = vol5 - buy_vol5
    strength5 = pd.Series(index=df5.index, dtype=float)
    strength5[:] = 100
    strength5[sell_vol5 > 1e-8] = (buy_vol5[sell_vol5 > 1e-8] / sell_vol5[sell_vol5 > 1e-8]) * 100
    strength5[sell_vol5 <= 1e-8] = 1000.0
    df5["Strength"] = strength5
    fast = config["MACD"]["fast_period"]; slow = config["MACD"]["slow_period"]; sig = config["MACD"]["signal_period"]
    macd_line5, signal_line5, hist5 = macd(df5["close"], fast, slow, sig)
    df5["MACD_line"] = macd_line5; df5["MACD_signal"] = signal_line5; df5["MACD_hist"] = hist5
    mfi_period = config["MFI"]["period"]
    df5[f"MFI_{mfi_period}"] = mfi(df5["high"], df5["low"], df5["close"], df5["volume"], mfi_period)
    stoch_k5, stoch_d5 = stochastic(df5["high"], df5["low"], df5["close"], stoch_k_period, stoch_d_period, stoch_smooth)
    df5[f"StochK_{stoch_k_period}"] = stoch_k5; df5[f"StochD_{stoch_k_period}"] = stoch_d5
    ichi_vals5 = ichimoku(df5["high"], df5["low"], df5["close"],
                          tenkan_period=ichi_cfg["tenkan_period"],
                          kijun_period=ichi_cfg["kijun_period"],
                          span_b_period=ichi_cfg["senkou_span_b_period"])
    df5["Tenkan"] = ichi_vals5["tenkan"]; df5["Kijun"] = ichi_vals5["kijun"]
    df5["SpanA"] = ichi_vals5["span_a"]; df5["SpanB"] = ichi_vals5["span_b"]; df5["Chikou"] = ichi_vals5["chikou"]
    adx_series5, di_plus5, di_minus5 = adx(df5["high"], df5["low"], df5["close"], adx_period)
    df5[f"ADX_{adx_period}"] = adx_series5; df5["DI_plus"] = di_plus5; df5["DI_minus"] = di_minus5
    df5["PSAR"] = parabolic_sar(df5["high"], df5["low"], sar_step, sar_max)
    for window in [5, 20, 60, 120]:
        if window <= len(df5):
            df5[f"MaxHigh{window}"] = df5["high"].rolling(window=window, min_periods=window).max()
            df5[f"MinLow{window}"] = df5["low"].rolling(window=window, min_periods=window).min()
        else:
            df5[f"MaxHigh{window}"] = df5["high"].rolling(window=window).max()
            df5[f"MinLow{window}"] = df5["low"].rolling(window=window).min()

    logging.debug(
        f"[{symbol}][F2][5분봉] 지표 계산 - EMA_5: {df5['EMA_5'].iloc[-1]}, EMA_20: {df5['EMA_20'].iloc[-1]}, RSI_14: {df5['RSI_14'].iloc[-1]}, ATR_14: {df5['ATR_14'].iloc[-1]}"
    )

    # ATR moving average used by some strategies
    df1[f"ATR_{atr_period}_MA20"] = df1[f"ATR_{atr_period}"].rolling(window=20, min_periods=20).mean()
    df5[f"ATR_{atr_period}_MA20"] = df5[f"ATR_{atr_period}"].rolling(window=20, min_periods=20).mean()
    
    # Evaluate each strategy's conditions on the latest data
    latest5 = df5.iloc[-1]  # latest completed 5m candle
    sync_ts = latest5["timestamp"]
    matching_1m = df1[df1["timestamp"] == sync_ts]
    if matching_1m.empty:
        logging.warning(
            f"[{symbol}] No matching 1m candle for 5m timestamp {sync_ts}. Skipping signal evaluation."
        )
        return {
            "symbol": symbol,
            "buy_signal": False,
            "sell_signal": False,
            "buy_triggers": [],
            "sell_triggers": [],
        }
    latest1 = matching_1m.iloc[-1]
    buy_signal = False
    sell_signal = False
    # Track strategies that triggered for transparency
    triggered_buys = []
    triggered_sells = []
    for strat in strategies:
        settings = STRATEGY_SETTINGS.get(strat["short_code"], {"on": True, "order": 999})
        if not settings.get("on", True):
            continue
        buy_formula = None
        sell_formula = None
        if "buy_formula_levels" in strat:
            buy_formula = strat["buy_formula_levels"][0]
        elif "buy_formula" in strat:
            buy_formula = strat["buy_formula"]

        if "sell_formula_levels" in strat:
            sell_formula = strat["sell_formula_levels"][0]
        elif "sell_formula" in strat:
            sell_formula = strat["sell_formula"]

        if buy_formula is None or sell_formula is None:
            logging.error(
                f"[{symbol}][F2][{strat.get('short_code','UNKNOWN')}] 전략 포뮬러가 없습니다"
            )
            continue
        logging.info(
            f"[{symbol}][F2][1분봉][{strat['short_code']}] 공식 평가 시작 - Buy: {buy_formula} | Sell: {sell_formula}"
        )
        try:
            buy_cond_1m = eval_formula(buy_formula, latest1, symbol, strat["short_code"])
            buy_cond_5m = eval_formula(buy_formula, latest5, symbol, strat["short_code"])
        except Exception as e:
            logging.error(
                f"[{symbol}][F2][{strat['short_code']}] 공식 평가 오류: {buy_formula} | 예외: {str(e)}"
            )
            buy_cond_1m = False
            buy_cond_5m = False
        try:
            sell_cond_1m = eval_formula(sell_formula, latest1, symbol, strat["short_code"])
        except Exception as e:
            logging.error(
                f"[{symbol}][F2][{strat['short_code']}] 공식 평가 오류: {sell_formula} | 예외: {str(e)}"
            )
            sell_cond_1m = False
        if buy_cond_1m and buy_cond_5m:
            buy_signal = True
            triggered_buys.append({"strategy": strat["short_code"], "formula": buy_formula, "order": settings.get("order", 999)})
        if sell_cond_1m:
            sell_signal = True
            triggered_sells.append({"strategy": strat["short_code"], "formula": sell_formula})
        logging.info(
            f"[{symbol}][F2][{strat['short_code']}] 평가 결과 - Buy_1m: {buy_cond_1m}, Buy_5m: {buy_cond_5m}, Sell_1m: {sell_cond_1m}"
        )
    if buy_signal:
        # Select the highest priority strategy among triggered ones
        triggered_buys.sort(key=lambda x: x.get("order", 999))
        top_strategy = triggered_buys[0]["strategy"]
        triggered_buys_codes = [top_strategy]
        logging.warning(
            f"[{symbol}][F2] BUY SIGNAL TRIGGERED - 전략: {triggered_buys_codes}"
        )
    else:
        triggered_buys_codes = []
    if sell_signal:
        triggered_sell_codes = [s['strategy'] for s in triggered_sells]
        logging.warning(
            f"[{symbol}][F2] SELL SIGNAL TRIGGERED - 전략: {triggered_sell_codes}"
        )

    result = {
        "symbol": symbol,
        "buy_signal": buy_signal,
        "sell_signal": sell_signal,
        "buy_triggers": triggered_buys_codes,
        "sell_triggers": [s["strategy"] for s in triggered_sells],
    }
    logging.debug(f"[{symbol}][F2] Result: {result}")
    return result

def eval_formula(formula: str, data_row: pd.Series, symbol: str = "", strat_code: str = "") -> bool:
    """
    Helper function to evaluate a buy/sell formula string on a given data row (Series of indicators).
    Returns True/False based on the formula conditions.
    """
    # Replace indicator references in the formula with actual numeric values from data_row
    expr = formula
    # Normalize some function names to match computed column names
    expr = expr.replace("MA(Vol,20)", "Vol_MA20")
    expr = expr.replace("MA(ATR(14),20)", "ATR_14_MA20")

    # Handle basic OHLCV fields with optional offsets like Close(-1)
    base_fields = {
        "Close": "close",
        "Open": "open",
        "High": "high",
        "Low": "low",
        "Vol": "volume",
    }
    for fld, col in base_fields.items():
        pattern = rf"{fld}\((-?[0-9]+)\)"
        def _repl(m):
            off = m.group(1)
            if off in ("0", "+0", ""):
                val = data_row.get(col, 0)
            else:
                val = 0
            return str(float(val))
        expr = re.sub(pattern, _repl, expr)
    # Handle indicators and fields present in data_row (like EMA(5), RSI(14), Close, etc.)
    # We will replace each known pattern with its value from data_row.
    # Note: It's important that longer names are replaced before shorter ones to avoid partial replacements.
    # For simplicity, replace in a careful order:
    # Replace literal 'Close', 'Open', 'High', 'Low', 'Vol' (volume) with respective values
    replacements = {
        "Close": data_row["close"],
        "Open": data_row["open"],
        "High": data_row["high"],
        "Low": data_row["low"],
        "Vol": data_row["volume"],  # shorthand for current volume
    }
    # Also replace 'EntryPrice', 'Entry', 'Peak' if present (if no position, these may not apply; assume False conditions if referenced)
    if "Entry" in formula or "EntryPrice" in formula:
        # For signal generation without position context, treat any Entry/Peak condition as False if no position.
        # (Alternatively, these could be handled externally when a position exists.)
        replacements["EntryPrice"] = replacements["Entry"] = replacements["Peak"] = 0  # placeholder
    # Prepare indicator patterns:
    # EMA, RSI, ATR, MFI, ADX, etc., with periods and optional offsets
    # We'll assume offset format as in formulas: e.g. "EMA(20)" or "EMA(20,-1)".
    # We handle common indicators:
    ind_patterns = ["EMA", "RSI", "ATR", "MFI", "ADX", "MACD_line", "MACD_signal", "MACD_hist",
                    "StochK", "StochD", "BB_upper", "BB_lower", "BB_mid",
                    "BandWidth20", "Vol_MA20", "ATR_14_MA20", "VWAP", "Strength",
                    "Tenkan", "Kijun", "SpanA", "SpanB", "Chikou",
                    "DI_plus", "DI_minus", "PSAR",
                    "MaxHigh5", "MaxHigh20", "MaxHigh60", "MaxHigh120",
                    "MinLow5", "MinLow20", "MinLow60", "MinLow120"]
    # Replace any known indicator mention with its value. We need to handle offsets like Indicator(period, offset).
    # We'll parse by finding occurrences of pattern names.
    for key in ind_patterns:
        if key in formula:
            # Determine if formula uses function-like syntax (with parentheses) or plain.
            # e.g. "EMA(5)" or "EMA(120,-1)" etc.
            # We'll do a simple replacement for specific cases:
            # Replace e.g. "EMA(5)" with data_row["EMA_5"], "EMA(5,-1)" means previous bar EMA5, which we can't get from single row.
            # To handle offsets in single row context: if offset refers to previous data, we cannot evaluate without full series.
            # For signals on latest row, any condition with offset referring to past can be approximated as False (or user should pass proper previous values).
            # Here, we assume formula evaluation is done on full series normally; for last row signals, skip offset logic.
            # We'll handle offset 0 explicitly:
            if key + "(" in formula:
                # Extract content inside parentheses
                # Example: key="EMA", formula segment "EMA(20)" or "EMA(20,-1)"
                pattern = rf"{key}\(([0-9]+)(?:,(-?[0-9]+))?\)"
                matches = re.finditer(pattern, expr)
                for m in matches:
                    period_val = m.group(1)
                    offset_val = m.group(2)
                    if key in ["EMA", "RSI", "ATR", "MFI", "ADX"]:
                        col_name = f"{key}_{period_val}"
                    elif key.startswith("Stoch"):
                        # e.g. StochK(14) -> StochK_14
                        col_name = f"{key}_{period_val}"
                    elif key.startswith("BB_") or key.startswith("BandWidth") or key.startswith("Vol_MA"):
                        # Already exact column names in DataFrame
                        col_name = key
                    else:
                        col_name = key  # for single series like Strength, VWAP, etc.
                    value = data_row.get(col_name, None)
                    # If offset is specified and not 0, we cannot get that from current row alone.
                    if offset_val is not None and offset_val not in ["0", ""]:
                        # If offset is negative (e.g., -1 for previous), we can't get previous from single row
                        # Here we assume evaluation on latest row only, so skip or treat as False condition.
                        # We'll replace with the current value as approximation or raise if needed.
                        # To be safe, if offset != 0, we assume condition cannot be verified here, return False.
                        value = None
                    # Replace the function call with the numeric value or a placeholder
                    if value is None or pd.isna(value):
                        # Use a value that will not trigger a buy/sell (for numeric comparisons, None will error; use 0 or some neutral)
                        replacement_val = "0"
                    else:
                        replacement_val = f"{float(value)}"
                    expr = re.sub(re.escape(m.group(0)), replacement_val, expr)
            else:
                # Plain key mention without parentheses
                if key in data_row:
                    expr = expr.replace(key, str(float(data_row[key])) if pd.notna(data_row[key]) else "0")
    # Replace basic fields after indicators (to avoid partial replacement issues)
    for name, val in replacements.items():
        expr = expr.replace(name, str(float(val)) if hasattr(val, "__float__") else str(val))
    # Replace mathematical symbols that might use '×' or '≤','≥' in the formula string with Python equivalents
    expr = expr.replace("×", "*").replace("≤", "<=").replace("≥", ">=")
    logging.debug(
        f"[{symbol}][F2][{strat_code}] 공식 치환: {formula} → {expr}"
    )
    # Evaluate the expression safely
    try:
        result = eval(expr)
        if isinstance(result, (int, float)):
            result = bool(result)
        logging.debug(
            f"[{symbol}][F2][{strat_code}] 평가값: {result}"
        )
        return bool(result)
    except Exception as e:
        logging.error(
            f"[{symbol}][F2][{strat_code}] 공식 평가 오류: {formula} | 예외: {str(e)}"
        )
        return False
