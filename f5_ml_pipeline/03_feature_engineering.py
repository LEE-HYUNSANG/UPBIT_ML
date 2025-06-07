"""03_feature_engineering 단계 확장형 스크립트."""

import logging
from pathlib import Path

import pandas as pd
import sys
sys.path.append(str(Path(__file__).resolve().parent.parent))
from indicators import (
    macd,
    mfi,
    adx,
    rsi,
    atr,
    stochastic,
    vwap,
)

from utils import ensure_dir, setup_logger

PIPELINE_ROOT = Path(__file__).resolve().parent
CLEAN_DIR = PIPELINE_ROOT / "ml_data" / "02_clean"
FEATURE_DIR = PIPELINE_ROOT / "ml_data" / "03_feature"
ROOT_DIR = PIPELINE_ROOT.parent
LOG_PATH = ROOT_DIR / "logs" / "f5" / "F5_ml_feature.log"


def add_features(df: pd.DataFrame) -> pd.DataFrame:
    """정제된 데이터프레임에 각종 지표/파생 컬럼을 추가."""
    df = df.copy()
    df.columns = [c.lower() for c in df.columns]

    required = {"open", "high", "low", "close", "volume"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Missing required columns: {', '.join(sorted(missing))}")

    # === 이동 평균 ===
    for span in [5, 8, 13, 20, 21, 60, 120]:
        df[f"ema{span}"] = df["close"].ewm(span=span, adjust=False).mean()
    for span in [5, 20]:
        df[f"sma{span}"] = df["close"].rolling(span).mean()
    df["ema5_ema20_diff"] = df["ema5"] - df["ema20"]
    df["ema8_ema21_diff"] = df["ema8"] - df["ema21"]
    df["ema5_ema60_diff"] = df["ema5"] - df["ema60"]
    df["ema20_ema60_diff"] = df["ema20"] - df["ema60"]
    df["ema_gc"] = (df["ema5"] > df["ema20"]).astype(int)
    df["ema_dc"] = (df["ema5"] < df["ema20"]).astype(int)

    # === 모멘텀 지표 ===
    df["rsi7"] = rsi(df["close"], period=7)
    df["rsi14"] = rsi(df["close"], period=14)
    df["rsi21"] = rsi(df["close"], period=21)
    df["rsi_oversold"] = (df["rsi14"] < 30).astype(int)
    df["rsi_overbought"] = (df["rsi14"] > 70).astype(int)
    df["atr14"] = atr(df["high"], df["low"], df["close"], period=14)

    df["ma_vol5"] = df["volume"].rolling(5).mean()
    df["ma_vol20"] = df["volume"].rolling(20).mean()
    df["vol_ratio"] = df["volume"] / (df["ma_vol20"] + 1e-8)
    df["vol_ratio_5"] = df["volume"] / (df["ma_vol5"] + 1e-8)
    df["vol_chg"] = df["volume"].pct_change().fillna(0)

    stoch_k7, stoch_d7 = stochastic(df["high"], df["low"], df["close"], k_period=7, d_period=3)
    stoch_k14, stoch_d14 = stochastic(df["high"], df["low"], df["close"], k_period=14, d_period=3)
    df["stoch_k7"] = stoch_k7
    df["stoch_d7"] = stoch_d7
    df["stoch_k14"] = stoch_k14
    df["stoch_d14"] = stoch_d14
    df["stoch_k"] = stoch_k14
    df["stoch_d"] = stoch_d14

    # === 파생 피처 및 변동률 ===

    # 가격변동률(1, 5, 10분)
    for p in [1, 5, 10]:
        df[f"pct_change_{p}m"] = df["close"].pct_change(p)
    df["mom10"] = df["close"].diff(10)
    df["roc10"] = df["close"].pct_change(10)

    # 캔들 신호/패턴/바디 비율
    df["is_bull"] = (df["close"] > df["open"]).astype(int)
    df["body_size"] = (df["close"] - df["open"]).abs()
    df["body_pct"] = df["body_size"] / (df["high"] - df["low"]).replace(0, 1)
    df["hl_range"] = df["high"] - df["low"]
    df["oc_range"] = (df["open"] - df["close"]).abs()
    df["body_to_range"] = df["body_size"] / (df["hl_range"] + 1e-8)

    # 간단한 캔들패턴
    upper_shadow = df["high"] - df[["open", "close"]].max(axis=1)
    lower_shadow = df[["open", "close"]].min(axis=1) - df["low"]
    df["is_doji"] = (df["body_size"] <= df["hl_range"] * 0.1).astype(int)
    df["long_bull"] = ((df["close"] > df["open"]) & (df["body_size"] >= df["hl_range"] * 0.7)).astype(int)
    df["long_bear"] = ((df["close"] < df["open"]) & (df["body_size"] >= df["hl_range"] * 0.7)).astype(int)
    df["is_hammer"] = ((lower_shadow >= 2 * df["body_size"]) & (upper_shadow <= df["body_size"])).astype(int)

    # 전봉 대비 변화/패턴
    df["close_change"] = df["close"].diff()
    df["high_break"] = (df["high"] > df["high"].shift(1)).astype(int)
    df["low_break"] = (df["low"] < df["low"].shift(1)).astype(int)
    df["pivot_up"] = ((df["close"] > df["open"]) & (df["close"].shift() < df["open"].shift())).astype(int)
    df["pivot_down"] = ((df["close"] < df["open"]) & (df["close"].shift() > df["open"].shift())).astype(int)

    # 볼린저밴드(20, 표준 2배수)
    ma20 = df["close"].rolling(20).mean()
    std20 = df["close"].rolling(20).std()
    df["bb_mid"] = ma20
    df["bb_upper"] = ma20 + 2 * std20
    df["bb_lower"] = ma20 - 2 * std20
    df["bb_width"] = (df["bb_upper"] - df["bb_lower"]) / (ma20 + 1e-8)
    df["bb_dist"] = (df["close"] - ma20) / (std20 + 1e-8)
    df["dis_ma20"] = (df["close"] - ma20) / (ma20 + 1e-8)
    df["volatility14"] = df["close"].pct_change().rolling(14).std()
    df["anomaly"] = ((df["close"] > df["bb_upper"]) | (df["close"] < df["bb_lower"])).astype(int)

    # MACD (12, 26, 9)
    macd_line, macd_signal, macd_hist = macd(df["close"])
    df["macd"] = macd_line
    df["macd_signal"] = macd_signal
    df["macd_hist"] = macd_hist

    # MFI와 ADX
    df["mfi14"] = mfi(df["high"], df["low"], df["close"], df["volume"], period=14)
    df["adx14"] = adx(df["high"], df["low"], df["close"], period=14)[0]
    typical_price = (df["high"] + df["low"] + df["close"]) / 3
    tp_mean = typical_price.rolling(14).mean()
    tp_dev = typical_price.rolling(14).apply(lambda x: (abs(x - x.mean())).mean(), raw=True)
    df["cci14"] = (typical_price - tp_mean) / (0.015 * tp_dev + 1e-8)
    df["vwap"] = vwap(df["high"], df["low"], df["close"], df["volume"])

    # OBV
    direction = df["volume"].where(df["close"] > df["close"].shift(), -df["volume"])
    df["obv"] = direction.cumsum().fillna(0)


    # 5분/일봉 변환
    if "timestamp" in df.columns:
        ts = pd.to_datetime(df["timestamp"])
        tmp = df.set_index(ts)
        res5 = tmp.resample("5min").agg({
            "open": "first",
            "high": "max",
            "low": "min",
            "close": "last",
            "volume": "sum",
        })
        res5 = res5.reindex(ts, method="ffill").add_prefix("m5_")
        df = pd.concat([df.reset_index(drop=True), res5.reset_index(drop=True)], axis=1)

        day_close = tmp["close"].resample("1D").last().reindex(ts, method="ffill")
        df["d_close"] = day_close.values

    # 거래대금/체결/호가 관련 피처(1분봉 데이터만으로 계산 불가)
    # if {"candle_acc_trade_price", "market_cap"}.issubset(df.columns):
    #     df["turnover"] = df["candle_acc_trade_price"] / df["market_cap"]
    # else:
    #     df["turnover"] = pd.NA

    # if {"ask_size", "bid_size"}.issubset(df.columns):
    #     total = df["ask_size"] + df["bid_size"]
    #     df["orderbook_ratio"] = df["bid_size"] / total.replace(0, pd.NA)
    # else:
    #     df["orderbook_ratio"] = pd.NA

    # if "acc_trade_price_24h" in df.columns:
    #     df["acc_trade_price_24h"] = df["acc_trade_price_24h"]
    # else:
    #     df["acc_trade_price_24h"] = pd.NA

    # if "acc_trade_volume_24h" in df.columns:
    #     df["acc_trade_volume_24h"] = df["acc_trade_volume_24h"]
    # else:
    #     df["acc_trade_volume_24h"] = pd.NA

    # if "signed_change_rate" in df.columns:
    #     df["change_rate"] = df["signed_change_rate"]
    # else:
    #     df["change_rate"] = pd.NA

    # for col in [
    #     "trade_strength",
    #     "large_trade",
    #     "trade_freq",
    #     "trade_dominance",
    #     "spread",
    # ]:
    #     if col not in df.columns:
    #         df[col] = pd.NA

    # === 시간 피처 (단타/ML 특화) ===
    # Datetime 인덱스가 없는 경우, candle_date_time_kst 등에서 추출 권장
    if "candle_date_time_kst" in df.columns:
        dt = pd.to_datetime(df["candle_date_time_kst"])
        df["hour"] = dt.dt.hour
        df["minute"] = dt.dt.minute
        df["dayofweek"] = dt.dt.dayofweek

    # 결측치/이상치 대체 - 숫자형 컬럼에 한해 inf 값 치환
    num_cols = df.select_dtypes(include="number").columns
    df[num_cols] = df[num_cols].replace([float("inf"), float("-inf")], pd.NA)
    df = df.ffill().bfill()

    # 필요 없는 컬럼 삭제(중간계산용)
    df = df.drop(columns=["ma_vol5", "ma_vol20"], errors="ignore")
    df = df.drop(columns=["return"], errors="ignore")

    return df


def process_file(file: Path) -> None:
    """단일 파케이 파일에 피처를 추가해 저장."""
    symbol = file.name.split("_")[0]
    output_path = FEATURE_DIR / f"{symbol}_feature.parquet"
    try:
        df = pd.read_parquet(file)
    except Exception as exc:
        logging.warning("%s 로드 실패: %s", file.name, exc)
        return

    try:
        df = add_features(df)
        df.to_parquet(output_path, index=False)
        logging.info(
            "[FEATURE] %s → %s, shape=%s",
            file.name,
            output_path.name,
            df.shape,
        )
    except Exception as exc:
        logging.warning("%s 저장 실패: %s", output_path.name, exc)


def main() -> None:
    """실행 엔트리 포인트."""
    ensure_dir(CLEAN_DIR)
    ensure_dir(FEATURE_DIR)
    setup_logger(LOG_PATH)

    for file in CLEAN_DIR.glob("*.parquet"):
        process_file(file)


if __name__ == "__main__":
    main()
