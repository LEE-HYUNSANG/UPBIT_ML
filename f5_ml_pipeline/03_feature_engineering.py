"""03_feature_engineering 단계 확장형 스크립트."""

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

import pandas as pd
import sys
sys.path.append(str(Path(__file__).resolve().parent.parent))
from indicators import macd, mfi, adx, sma, vwap

from utils import ensure_dir

PIPELINE_ROOT = Path(__file__).resolve().parent
CLEAN_DIR = PIPELINE_ROOT / "ml_data" / "02_clean"
FEATURE_DIR = PIPELINE_ROOT / "ml_data" / "03_feature"
LOG_PATH = PIPELINE_ROOT / "logs" / "ml_feature.log"


def setup_logger() -> None:
    """로그 설정."""
    ensure_dir(LOG_PATH.parent)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            RotatingFileHandler(
                LOG_PATH,
                encoding="utf-8",
                maxBytes=50_000 * 1024,
                backupCount=5,
            ),
            logging.StreamHandler(),
        ],
        force=True,
    )


def add_features(df: pd.DataFrame) -> pd.DataFrame:
    """정제된 데이터프레임에 각종 지표/파생 컬럼을 추가."""
    df = df.copy()
    df.columns = [c.lower() for c in df.columns]

    required = {"open", "high", "low", "close", "volume"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Missing required columns: {', '.join(sorted(missing))}")

    # === 표준 피처 ===

    # EMA 및 장기선
    ##df["ema5"] = df["close"].ewm(span=5, adjust=False).mean()
    ##df["ema8"] = df["close"].ewm(span=8, adjust=False).mean()
    ##df["ema13"] = df["close"].ewm(span=13, adjust=False).mean()
    ##df["ema20"] = df["close"].ewm(span=20, adjust=False).mean()
    ##df["ema21"] = df["close"].ewm(span=21, adjust=False).mean()
    ##df["ema60"] = df["close"].ewm(span=60, adjust=False).mean()
    ##df["ema120"] = df["close"].ewm(span=120, adjust=False).mean()

    # SMA
    df["sma5"] = df["close"].rolling(window=5).mean()
    ##df["sma20"] = df["close"].rolling(window=20).mean()

    # EMA 차이
    df["ema5_ema20_diff"] = df["ema5"] - df["ema20"]
    ##df["ema8_ema21_diff"] = df["ema8"] - df["ema21"]
    ##df["ema5_ema60_diff"] = df["ema5"] - df["ema60"]
    ##df["ema20_ema60_diff"] = df["ema20"] - df["ema60"]

    # EMA 골든/데드크로스 flag
    df["ema_gc"] = ((df["ema5"].shift(1) < df["ema20"].shift(1)) & (df["ema5"] > df["ema20"])).astype(int)
    ##df["ema_dc"] = ((df["ema5"].shift(1) > df["ema20"].shift(1)) & (df["ema5"] < df["ema20"])).astype(int)

    # RSI
    for w in [7, 14, 21]:
        delta = df["close"].diff()
        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)
        avg_gain = gain.rolling(w).mean()
        avg_loss = loss.rolling(w).mean()
        rs = avg_gain / (avg_loss + 1e-8)
        df[f"rsi{w}"] = 100 - (100 / (1 + rs))
        # 과매수/과매도 flag
        if w == 14:
            df["rsi_oversold"] = (df[f"rsi{w}"] < 30).astype(int)
            df["rsi_overbought"] = (df[f"rsi{w}"] > 70).astype(int)

    # ATR
    ##for w in [7, 14]:
    ##    high_low = df["high"] - df["low"]
    ##    high_close = (df["high"] - df["close"].shift()).abs()
    ##    low_close = (df["low"] - df["close"].shift()).abs()
    ##    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    ##    df[f"atr{w}"] = tr.rolling(window=w).mean()

    # 볼륨 평균/비율/증감
    ## df["ma_vol5"] = df["volume"].rolling(5).mean()
    ## df["ma_vol20"] = df["volume"].rolling(20).mean()
    ## df["vol_ratio"] = df["volume"] / (df["ma_vol20"] + 1e-8)
    ## df["vol_ratio_5"] = df["volume"] / (df["ma_vol5"] + 1e-8)
    ## df["vol_chg"] = df["volume"].pct_change().fillna(0)

    # 스토캐스틱
    for w in [7, 14]:
        low_w = df["low"].rolling(w).min()
        high_w = df["high"].rolling(w).max()
        stoch_k = 100 * (df["close"] - low_w) / (high_w - low_w + 1e-8)
        df[f"stoch_k{w}"] = stoch_k
        df[f"stoch_d{w}"] = stoch_k.rolling(3).mean()

    # 일반화된 %K, %D(14)
    ##df["stoch_k"] = df["stoch_k14"]
    ##df["stoch_d"] = df["stoch_d14"]

    # === 추가 파생 피처/캔들/변동률/볼린저 ===

    # 가격변동률(1, 5, 10분)
    for p in [1, 5, 10]:
        df[f"pct_change_{p}m"] = df["close"].pct_change(p)

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

    # MACD (12, 26, 9)
    macd_line, macd_signal, macd_hist = macd(df["close"])
    df["macd"] = macd_line
    df["macd_signal"] = macd_signal
    df["macd_hist"] = macd_hist

    # MFI와 ADX
    ##df["mfi14"] = mfi(df["high"], df["low"], df["close"], df["volume"], period=14)
    ##df["adx14"] = adx(df["high"], df["low"], df["close"], period=14)[0]

    # MOM/ROC(10)
    ##df["mom10"] = df["close"] - df["close"].shift(10)
    ##df["roc10"] = (df["close"] / df["close"].shift(10) - 1) * 100

    # CCI(14)
    ##tp = (df["high"] + df["low"] + df["close"]) / 3
    ##sma_tp = tp.rolling(14).mean()
    ##mean_dev = (tp - sma_tp).abs().rolling(14).mean()
    ##df["cci14"] = (tp - sma_tp) / (0.015 * (mean_dev + 1e-8))

    # VWAP
    try:
        df["vwap"] = vwap(df["high"], df["low"], df["close"], df["volume"])
    except Exception:
        df["vwap"] = pd.NA

    # OBV
    ##direction = df["volume"].where(df["close"] > df["close"].shift(), -df["volume"])
    ##df["obv"] = direction.cumsum().fillna(0)

    # 변동성 지표 및 이상값 탐지
    df["return"] = df["close"].pct_change()
    df["volatility14"] = df["return"].rolling(14).std()
    df["anomaly"] = (df["return"].abs() > 3 * df["volatility14"]).astype(int)

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

    # 거래대금/체결/호가 관련 피처(데이터 없을 시 NA)
    if {"candle_acc_trade_price", "market_cap"}.issubset(df.columns):
        df["turnover"] = df["candle_acc_trade_price"] / df["market_cap"]
    else:
        df["turnover"] = pd.NA

    if {"ask_size", "bid_size"}.issubset(df.columns):
        total = df["ask_size"] + df["bid_size"]
        df["orderbook_ratio"] = df["bid_size"] / total.replace(0, pd.NA)
    else:
        df["orderbook_ratio"] = pd.NA

    if "acc_trade_price_24h" in df.columns:
        df["acc_trade_price_24h"] = df["acc_trade_price_24h"]
    else:
        df["acc_trade_price_24h"] = pd.NA

    if "acc_trade_volume_24h" in df.columns:
        df["acc_trade_volume_24h"] = df["acc_trade_volume_24h"]
    else:
        df["acc_trade_volume_24h"] = pd.NA

    if "signed_change_rate" in df.columns:
        df["change_rate"] = df["signed_change_rate"]
    else:
        df["change_rate"] = pd.NA

    for col in [
        "trade_strength",
        "large_trade",
        "trade_freq",
        "trade_dominance",
        "spread",
    ]:
        if col not in df.columns:
            df[col] = pd.NA

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
    setup_logger()

    for file in CLEAN_DIR.glob("*.parquet"):
        process_file(file)


if __name__ == "__main__":
    main()
