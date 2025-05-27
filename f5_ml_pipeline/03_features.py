"""Feature engineering for ML pipeline.

Reads cleaned OHLCV parquet files from ``ml_data/02_clean/`` and writes
indicator enriched parquet files to ``ml_data/03_features/`` with the same
filenames.

New columns
===========
- ``ema_5``/``ema_20``/``ema_60``: exponential moving averages of ``close``
- ``atr_14``: average true range
- ``rsi_14``: relative strength index
- ``ma_vol_20``: 20 period moving average of ``volume``
- ``max_high_5``/``20``/``60``/``120``: rolling maximum of ``high``
- ``min_low_5``/``20``/``60``/``120``: rolling minimum of ``low``
- ``stoch_k_14`` and ``stoch_d_14``: stochastic oscillator
- ``bb_mid_20_2``, ``bb_upper_20_2``, ``bb_lower_20_2``: Bollinger Bands
- ``mfi_14``: money flow index
- ``vwap``: volume weighted average price
- ``psar``: parabolic SAR
- ``tenkan_9``, ``kijun_26``, ``span_a``, ``span_b``, ``max_span``: Ichimoku lines
- ``strength``: volume based strength approximation
- ``buy_qty_5m``/``sell_qty_5m``: placeholders requiring collector data
- ``*_prev1``/``*_prev2``: shifted OHLC values
- ``rsi_14_prev1`` and ``mfi_14_prev1``: previous indicator values
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from pathlib import Path
from indicators import (
    ema,
    atr,
    rsi,
    bollinger_bands,
    stochastic,
    mfi,
    vwap,
    ichimoku,
    parabolic_sar,
)

BASE_DIR = Path(__file__).resolve().parent
CLEAN_DIR = BASE_DIR / "ml_data/02_clean"
FEATURE_DIR = BASE_DIR / "ml_data/03_features"


def _detect_time_column(df: pd.DataFrame) -> str | None:
    candidates = [c for c in df.columns if "time" in c or "date" in c]
    for col in [
        "timestamp",
        "candle_date_time_utc",
        "candle_date_time_kst",
        "datetime",
    ] + candidates:
        if col in df.columns:
            return col
    return None


def _calc_strength(df: pd.DataFrame) -> pd.Series:
    high = df["high"]
    low = df["low"]
    close = df["close"]
    volume = df["volume"]
    rng = (high - low).replace(0, np.nan)
    multiplier = (2 * close - high - low) / rng
    multiplier = multiplier.fillna(0)
    buy_vol = (multiplier + 1) / 2 * volume
    sell_vol = volume - buy_vol
    strength = pd.Series(100.0, index=df.index)
    mask = sell_vol > 1e-8
    strength[mask] = (buy_vol[mask] / sell_vol[mask]) * 100
    strength[~mask] = 1000.0
    return strength


def compute_features(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    time_col = _detect_time_column(df)
    if time_col:
        df.sort_values(time_col, inplace=True)
    df["ema_5"] = ema(df["close"], 5)
    df["ema_20"] = ema(df["close"], 20)
    df["ema_60"] = ema(df["close"], 60)
    df["atr_14"] = atr(df["high"], df["low"], df["close"], 14)
    df["rsi_14"] = rsi(df["close"], 14)
    df["ma_vol_20"] = df["volume"].rolling(window=20, min_periods=20).mean()
    for w in [5, 20, 60, 120]:
        df[f"max_high_{w}"] = df["high"].rolling(window=w, min_periods=w).max()
        df[f"min_low_{w}"] = df["low"].rolling(window=w, min_periods=w).min()
    bb_mid, bb_up, bb_low = bollinger_bands(df["close"], 20, 2)
    df["bb_mid_20_2"] = bb_mid
    df["bb_upper_20_2"] = bb_up
    df["bb_lower_20_2"] = bb_low
    stoch_k, stoch_d = stochastic(df["high"], df["low"], df["close"], 14, 3, 3)
    df["stoch_k_14"] = stoch_k
    df["stoch_d_14"] = stoch_d
    df["mfi_14"] = mfi(df["high"], df["low"], df["close"], df["volume"], 14)
    df["vwap"] = vwap(df["high"], df["low"], df["close"], df["volume"])
    df["psar"] = parabolic_sar(df["high"], df["low"])
    ichi = ichimoku(df["high"], df["low"], df["close"])
    df["tenkan_9"] = ichi["tenkan"]
    df["kijun_26"] = ichi["kijun"]
    df["span_a"] = ichi["span_a"]
    df["span_b"] = ichi["span_b"]
    df["max_span"] = np.maximum(df["span_a"], df["span_b"])
    df["strength"] = _calc_strength(df)
    for col in ["close", "open", "high", "low"]:
        df[f"{col}_prev1"] = df[col].shift(1)
        df[f"{col}_prev2"] = df[col].shift(2)
    df["rsi_14_prev1"] = df["rsi_14"].shift(1)
    df["mfi_14_prev1"] = df["mfi_14"].shift(1)
    df["buy_qty_5m"] = np.nan
    df["sell_qty_5m"] = np.nan
    return df


def main() -> None:
    FEATURE_DIR.mkdir(parents=True, exist_ok=True)
    if not CLEAN_DIR.exists():
        print(f"Clean directory {CLEAN_DIR} missing")
        return
    files = list(CLEAN_DIR.glob("*.parquet"))
    if not files:
        print("No cleaned parquet files found")
        return
    for path in files:
        print(f"Processing {path.name}")
        df = pd.read_parquet(path)
        feat = compute_features(df)
        out_path = FEATURE_DIR / path.name
        feat.to_parquet(out_path, index=False, compression="zstd")
        print(f"Saved features to {out_path}")


if __name__ == "__main__":
    main()
