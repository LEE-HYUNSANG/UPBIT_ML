import json
import time
from typing import List

import pandas as pd
from sklearn.linear_model import LogisticRegression

from indicators import ema, sma, rsi


def fetch_ohlcv(symbol: str, count: int = 60) -> pd.DataFrame:
    """Fetch recent OHLCV data with up to three retries."""
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


def _preprocess(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["return"] = df["close"].pct_change()
    df["rsi"] = rsi(df["close"], 14)
    df["ema5"] = ema(df["close"], 5)
    df["ema20"] = ema(df["close"], 20)
    df["ema_diff"] = df["ema5"] - df["ema20"]
    df["vol_ma20"] = sma(df["volume"], 20)
    df["vol_ratio"] = df["volume"] / df["vol_ma20"]
    df["target"] = (df["close"].shift(-5) > df["close"]).astype(int)
    df.dropna(inplace=True)
    return df


def _train_predict(df: pd.DataFrame) -> bool:
    features = ["return", "rsi", "ema_diff", "vol_ratio"]
    train_df = df.iloc[:-1]
    if train_df.empty or train_df["target"].nunique() < 2:
        return False
    X = train_df[features]
    y = train_df["target"]
    model = LogisticRegression()
    model.fit(X, y)
    last_row = df.iloc[-1][features].values.reshape(1, -1)
    prob = model.predict_proba(last_row)[0][1]
    return prob > 0.5


def check_buy_signal(symbol: str) -> bool:
    df = fetch_ohlcv(symbol)
    if df.empty or len(df) < 30:
        return False
    df = _preprocess(df)
    if df.empty:
        return False
    return _train_predict(df)


def check_buy_signal_df(df: pd.DataFrame) -> bool:
    if df.empty or len(df) < 30:
        return False
    df = _preprocess(df)
    if df.empty:
        return False
    return _train_predict(df)


def run() -> List[str]:
    try:
        with open("config/coin_list_monitoring.json", "r", encoding="utf-8") as f:
            coins = json.load(f)
    except Exception:
        coins = []
    results = []
    for sym in coins:
        if check_buy_signal(sym):
            results.append(sym)
    with open("config/coin_realtime_buy_list.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    return results


if __name__ == "__main__":
    run()
