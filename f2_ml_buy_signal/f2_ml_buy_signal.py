"""Lightweight ML pipeline for real-time buy signals."""

from __future__ import annotations

import json
import logging
import sys
import time
from pathlib import Path
from typing import List, Tuple

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
    import joblib
except ImportError as exc:  # pragma: no cover - dependency missing at runtime
    logging.exception("Required dependency missing: %s", exc)
    sys.exit(1)

from indicators import ema, sma, rsi  # type: ignore
from f5_ml_pipeline.utils import ensure_dir
CONFIG_DIR = PROJECT_ROOT / "config"

DATA_ROOT = PROJECT_ROOT / "f2_ml_buy_signal" / "f2_data"
RAW_DIR = DATA_ROOT / "01_data"
CLEAN_DIR = DATA_ROOT / "02_clean_data"
FEATURE_DIR = DATA_ROOT / "03_data"
LABEL_DIR = DATA_ROOT / "04_data"
SPLIT_DIR = DATA_ROOT / "05_data"
MODEL_DIR = DATA_ROOT / "06_data"


def _load_json(path: Path):
    if not path.exists():
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _save_json(path: Path, data) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def fetch_ohlcv(symbol: str, count: int = 60) -> pd.DataFrame:
    """Fetch recent OHLCV data with retries."""
    logging.info("[FETCH] %s count=%d", symbol, count)
    try:
        import pyupbit  # type: ignore
    except Exception:
        return pd.DataFrame()

    for _ in range(3):
        try:
            df = pyupbit.get_ohlcv(symbol, interval="minute1", count=count)
            if df is not None:
                df = df.reset_index().rename(columns={"index": "timestamp"})
                logging.info("[FETCH] %s rows=%d", symbol, len(df))
                ensure_dir(RAW_DIR)
                out_path = RAW_DIR / f"{symbol}.parquet"
                try:
                    df.to_parquet(out_path, index=False)
                    logging.info("[FETCH] saved %s", out_path.name)
                except Exception:
                    logging.warning("[FETCH] save failed %s", out_path.name)
                return df
        except Exception:
            time.sleep(0.2)
    logging.warning("[FETCH] %s failed", symbol)
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


def _split_df(df: pd.DataFrame, train_ratio: float = 0.7,
              valid_ratio: float = 0.2) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    n = len(df)
    n_train = int(n * train_ratio)
    n_valid = int(n * valid_ratio)
    train = df.iloc[:n_train]
    valid = df.iloc[n_train:n_train + n_valid]
    test = df.iloc[n_train + n_valid:]
    return train, valid, test


def _train_predict(df: pd.DataFrame, symbol: str) -> bool:
    features = ["return", "rsi", "ema_diff", "vol_ratio"]
    train_df, valid_df, test_df = _split_df(df)

    ensure_dir(SPLIT_DIR)
    for part, data in {"train": train_df, "valid": valid_df, "test": test_df}.items():
        out = SPLIT_DIR / f"{symbol}_{part}.parquet"
        try:
            data.to_parquet(out, index=False)
            logging.info("[SPLIT] saved %s", out.name)
        except Exception:
            logging.warning("[SPLIT] save failed %s", out.name)

    if train_df.empty or train_df["label"].nunique() < 2:
        logging.info("[TRAIN] %s skipped due to insufficient data", symbol)
        return False

    X = train_df[features]
    y = train_df["label"]
    model = LogisticRegression(max_iter=200, solver="liblinear")
    model.fit(X, y)

    ensure_dir(MODEL_DIR)
    model_path = MODEL_DIR / f"{symbol}_model.pkl"
    try:
        joblib.dump(model, model_path)
        logging.info("[TRAIN] saved model %s", model_path.name)
    except Exception:
        logging.warning("[TRAIN] save failed %s", model_path.name)

    last_row = df.iloc[[-1]][features]
    prob = model.predict_proba(last_row)[0][1]
    logging.info("[PREDICT] prob=%.4f", prob)
    return prob > 0.5


def check_buy_signal(symbol: str) -> bool:
    df = fetch_ohlcv(symbol)
    if df.empty or len(df) < 30:
        logging.info("[CHECK] %s insufficient data", symbol)
        return False

    df = _clean_df(df)
    ensure_dir(CLEAN_DIR)
    clean_path = CLEAN_DIR / f"{symbol}.parquet"
    try:
        df.to_parquet(clean_path, index=False)
        logging.info("[CLEAN] saved %s", clean_path.name)
    except Exception:
        logging.warning("[CLEAN] save failed %s", clean_path.name)

    df = _add_features(df)
    ensure_dir(FEATURE_DIR)
    feat_path = FEATURE_DIR / f"{symbol}.parquet"
    try:
        df.to_parquet(feat_path, index=False)
        logging.info("[FEATURE] saved %s", feat_path.name)
    except Exception:
        logging.warning("[FEATURE] save failed %s", feat_path.name)

    df = _label(df)
    if df.empty:
        logging.info("[CHECK] %s no labeled rows", symbol)
        return False

    ensure_dir(LABEL_DIR)
    label_path = LABEL_DIR / f"{symbol}.parquet"
    try:
        df.to_parquet(label_path, index=False)
        logging.info("[LABEL] saved %s", label_path.name)
    except Exception:
        logging.warning("[LABEL] save failed %s", label_path.name)

    return _train_predict(df, symbol)


def check_buy_signal_df(df: pd.DataFrame, symbol: str = "df") -> bool:
    if df.empty or len(df) < 30:
        logging.info("[CHECK_DF] insufficient rows")
        return False
    df = _clean_df(df)
    df = _add_features(df)
    df = _label(df)
    if df.empty:
        logging.info("[CHECK_DF] no labeled rows")
        return False
    return _train_predict(df, symbol)


def run() -> List[str]:
    logging.info("[RUN] starting buy signal scan")
    try:
        with open(CONFIG_DIR / "coin_list_monitoring.json", "r", encoding="utf-8") as f:
            coins = json.load(f)
    except Exception:
        coins = []

    logging.info("[RUN] coins=%s", coins)
    buy_list_path = CONFIG_DIR / "coin_realtime_buy_list.json"
    sell_list_path = CONFIG_DIR / "coin_realtime_sell_list.json"
    buy_dict = _load_json(buy_list_path)
    sell_dict = _load_json(sell_list_path)
    risk_cfg = _load_json(CONFIG_DIR / "risk.json")

    results = []
    for sym in coins:
        buy = check_buy_signal(sym)
        logging.info("[%s] buy_signal=%s", sym, int(buy))
        if buy:
            results.append(sym)
            if sym not in buy_dict:
                buy_dict[sym] = 0
                sell_dict.setdefault(
                    sym,
                    {
                        "SL_PCT": risk_cfg.get("SL_PCT"),
                        "TP_PCT": risk_cfg.get("TP_PCT"),
                        "TRAILING_STOP_ENABLED": risk_cfg.get("TRAILING_STOP_ENABLED"),
                        "TRAIL_START_PCT": risk_cfg.get("TRAIL_START_PCT"),
                        "TRAIL_STEP_PCT": risk_cfg.get("TRAIL_STEP_PCT"),
                    },
                )

    _save_json(buy_list_path, buy_dict)
    _save_json(sell_list_path, sell_dict)

    logging.info("[RUN] finished. %d coins to buy", len(results))
    return results


if __name__ == "__main__":
    run()
