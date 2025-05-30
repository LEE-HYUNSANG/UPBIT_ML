"""Lightweight ML pipeline for real-time buy signals."""

from __future__ import annotations

import json
import logging
import sys
import time
from pathlib import Path
from typing import List

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(PROJECT_ROOT))

LOG_PATH = PROJECT_ROOT / "logs" / "f2_ml_buy_signal.log"


def setup_logger() -> None:
    """Configure basic logger."""
    LOG_PATH.parent.mkdir(exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [F2] [%(levelname)s] %(message)s",
        handlers=[logging.StreamHandler(), logging.FileHandler(LOG_PATH)],
        force=True,
    )


setup_logger()

try:
    import pandas as pd
    from sklearn.linear_model import LogisticRegression
except ImportError as exc:  # pragma: no cover - dependency missing at runtime
    logging.exception("Required dependency missing: %s", exc)
    sys.exit(1)

from indicators import ema, sma, rsi  # type: ignore
CONFIG_DIR = PROJECT_ROOT / "config"


def fetch_ohlcv(symbol: str, count: int = 60) -> pd.DataFrame:
    """Fetch recent OHLCV data with retries."""
    try:
        import pyupbit  # type: ignore
    except Exception:
        return pd.DataFrame()

    for _ in range(3):
        try:
            df = pyupbit.get_ohlcv(symbol, interval="minute1", count=count)
            if df is not None:
                df = df.reset_index().rename(columns={"index": "timestamp"})
                return df
        except Exception:
            time.sleep(0.2)
    return pd.DataFrame()


def _clean_df(df: pd.DataFrame) -> pd.DataFrame:
    df = df.drop_duplicates("timestamp").sort_values("timestamp")
    df = df.ffill().bfill().reset_index(drop=True)
    return df


def _add_features(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["return"] = df["close"].pct_change()
    df["rsi"] = rsi(df["close"], 14)
    df["ema5"] = ema(df["close"], 5)
    df["ema20"] = ema(df["close"], 20)
    df["ema_diff"] = df["ema5"] - df["ema20"]
    df["vol_ma20"] = sma(df["volume"], 20)
    df["vol_ratio"] = df["volume"] / df["vol_ma20"]
    df.dropna(inplace=True)
    return df


def _label(df: pd.DataFrame, horizon: int = 5) -> pd.DataFrame:
    df = df.copy()
    df["label"] = (df["close"].shift(-horizon) > df["close"]).astype(int)
    df.dropna(inplace=True)
    return df


def _train_predict(df: pd.DataFrame) -> bool:
    features = ["return", "rsi", "ema_diff", "vol_ratio"]
    train_df = df.iloc[:-1]
    if train_df.empty or train_df["label"].nunique() < 2:
        return False
    X = train_df[features]
    y = train_df["label"]
    model = LogisticRegression(max_iter=200, solver="liblinear")
    model.fit(X, y)
    last_row = df.iloc[[-1]][features]
    prob = model.predict_proba(last_row)[0][1]
    return prob > 0.5


def check_buy_signal(symbol: str) -> bool:
    df = fetch_ohlcv(symbol)
    if df.empty or len(df) < 30:
        return False
    df = _clean_df(df)
    df = _add_features(df)
    df = _label(df)
    if df.empty:
        return False
    return _train_predict(df)


def check_buy_signal_df(df: pd.DataFrame) -> bool:
    if df.empty or len(df) < 30:
        return False
    df = _clean_df(df)
    df = _add_features(df)
    df = _label(df)
    if df.empty:
        return False
    return _train_predict(df)


def run() -> List[str]:
    try:
        with open(CONFIG_DIR / "coin_list_monitoring.json", "r", encoding="utf-8") as f:
            coins = json.load(f)
    except Exception:
        coins = []

    results = []
    for sym in coins:
        buy = check_buy_signal(sym)
        logging.info("[%s] buy_signal=%s", sym, int(buy))
        if buy:
            results.append(sym)

    with open(CONFIG_DIR / "coin_realtime_buy_list.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    return results


if __name__ == "__main__":
    run()
