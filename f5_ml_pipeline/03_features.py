"""클린된 OHLCV 데이터에 각종 지표 컬럼을 추가해 저장합니다.

생성 컬럼
=========
- ``ema_5``/``ema_20``/``ema_60``: 지수 이동평균
- ``atr_14``: 평균 진폭
- ``rsi_14``: RSI 지표
- ``ma_vol_20``: 거래량 20일 이동평균
- ``max_high_N``/``min_low_N``: 고가·저가 rolling 값
- ``bb_mid_20_2``/``bb_upper_20_2``/``bb_lower_20_2``: 볼린저밴드
- ``stoch_k_14``/``stoch_d_14``: 스토캐스틱
- ``mfi_14``: MFI 지표
- ``vwap``: VWAP
- ``psar``: 파라볼릭 SAR
- ``tenkan_9``/``kijun_26``/``span_a``/``span_b``/``span_a_26``/``span_b_26``
  ``max_span``/``maxspan``: 이치모쿠 관련
- ``strength``: 거래 강도 근사치
- ``buy_qty_5m``/``sell_qty_5m``: 추후 Collector에서 결합
- ``*_prev1``/``*_prev2``: 시프트된 OHLCV 값
- ``rsi_14_prev1``/``mfi_14_prev1``: 이전 지표 값
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

    # === 1. 필수 원본 컬럼명 지정 ===
    time_col = _detect_time_column(df)
    if time_col:
        df.sort_values(time_col, inplace=True)

    # === 2. EMA, ATR, RSI ===
    df["ema_5"] = ema(df["close"], 5)
    df["ema_20"] = ema(df["close"], 20)
    df["ema_60"] = ema(df["close"], 60)
    df["atr_14"] = atr(df["high"], df["low"], df["close"], 14)
    df["rsi_14"] = rsi(df["close"], 14)

    # === 3. 볼린저밴드 ===
    bb_mid, bb_up, bb_low = bollinger_bands(df["close"], 20, 2)
    df["bb_mid_20_2"] = bb_mid
    df["bb_upper_20_2"] = bb_up
    df["bb_lower_20_2"] = bb_low

    # === 4. Stochastic K/D ===
    stoch_k, stoch_d = stochastic(df["high"], df["low"], df["close"], 14, 3, 3)
    df["stoch_k_14"] = stoch_k
    df["stoch_d_14"] = stoch_d

    # === 5. MFI(14) ===
    df["mfi_14"] = mfi(df["high"], df["low"], df["close"], df["volume"], 14)

    # === 6. MaxHighN, MinLowN ===
    for w in [5, 20, 60, 120]:
        df[f"max_high_{w}"] = df["high"].rolling(window=w, min_periods=w).max()
        df[f"min_low_{w}"] = df["low"].rolling(window=w, min_periods=w).min()

    # === 7. MA(Vol,20), Vol(0) ===
    df["ma_vol_20"] = df["volume"].rolling(window=20, min_periods=20).mean()
    df["vol_0"] = df["volume"]

    # 기타 지표 계산
    df["vwap"] = vwap(df["high"], df["low"], df["close"], df["volume"])
    df["psar"] = parabolic_sar(df["high"], df["low"])
    ichi = ichimoku(df["high"], df["low"], df["close"])
    df["tenkan_9"] = ichi["tenkan"]
    df["kijun_26"] = ichi["kijun"]
    df["span_a"] = ichi["span_a"]
    df["span_b"] = ichi["span_b"]
    df["span_a_26"] = df["span_a"].shift(26)
    df["span_b_26"] = df["span_b"].shift(26)
    df["max_span"] = np.maximum(df["span_a"], df["span_b"])
    df["maxspan"] = df[["span_a", "span_b"]].max(axis=1)

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
