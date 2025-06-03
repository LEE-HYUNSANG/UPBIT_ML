"""Lightweight ML pipeline for real-time buy signals."""

from __future__ import annotations

import importlib.util
import json
import logging
import sys
import time
from pathlib import Path
from typing import List, Tuple
import shutil
from common_utils import ensure_utf8_stdout

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(PROJECT_ROOT))

LOG_PATH = PROJECT_ROOT / "logs" / "f2" / "f2_ml_buy_signal.log"


def setup_logger() -> None:
    """Configure basic logger."""
    # Ensure the logs directory exists even if the entire tree was removed.
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    ensure_utf8_stdout()
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
from common_utils import load_json, save_json
try:
    spec = importlib.util.spec_from_file_location(
        "buy_indicator", Path(__file__).with_name("01_buy_indicator.py")
    )
    f2_buy_indicator = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(f2_buy_indicator)
except Exception:  # pragma: no cover - handle missing module
    f2_buy_indicator = None  # type: ignore

PIPELINE_ROOT = PROJECT_ROOT / "f5_ml_pipeline"
if str(PIPELINE_ROOT) not in sys.path:
    sys.path.append(str(PIPELINE_ROOT))

def _load_module(filename: str, name: str):
    path = PIPELINE_ROOT / filename
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module

P01 = P02 = P03 = P04 = P05 = P06 = P08 = None

def _ensure_pipeline_modules() -> None:
    """Load pipeline modules on demand."""
    global P01, P02, P03, P04, P05, P06, P08
    if P01 is None:
        P01 = _load_module("01_data_collect.py", "p01")
        P02 = _load_module("02_data_cleaning.py", "p02")
        P03 = _load_module("03_feature_engineering.py", "p03")
        P04 = _load_module("04_labeling.py", "p04")
        P05 = _load_module("05_split.py", "p05")
        P06 = _load_module("06_train.py", "p06")
        P08 = _load_module("08_predict.py", "p08")
CONFIG_DIR = PROJECT_ROOT / "config"

DATA_ROOT = PROJECT_ROOT / "f2_ml_buy_signal" / "f2_data"
RAW_DIR = DATA_ROOT / "01_data"
CLEAN_DIR = DATA_ROOT / "02_clean_data"
FEATURE_DIR = DATA_ROOT / "03_data"
LABEL_DIR = DATA_ROOT / "04_data"
SPLIT_DIR = DATA_ROOT / "05_data"
MODEL_DIR = DATA_ROOT / "06_data"


def cleanup_data_dir() -> None:
    """Remove temporary data directory created during checks."""
    if DATA_ROOT.exists():
        try:
            shutil.rmtree(DATA_ROOT)
            logging.info("[CLEANUP] removed %s", DATA_ROOT)
        except Exception:
            logging.warning("[CLEANUP] failed to remove %s", DATA_ROOT)




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
    """Label dataset using the same threshold settings as the F5 module."""
    _ensure_pipeline_modules()
    thresh = getattr(P04, "THRESH_LIST", [0.002])[0]
    loss = getattr(P04, "LOSS_LIST", [thresh])[0]
    labeled = P04.make_labels_basic(df, horizon, thresh, loss)
    labeled["label"] = (labeled["label"] == 1).astype(int)
    labeled.dropna(inplace=True)
    return labeled


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


def run_pipeline_for_symbol(symbol: str) -> None:
    """Execute the F5 ML pipeline for ``symbol`` once."""
    _ensure_pipeline_modules()
    try:
        P01.collect_once([symbol])
    except Exception:
        logging.exception("[PIPELINE] data_collect failed for %s", symbol)

    raw_file = P01.DATA_ROOT / f"{symbol}_rawdata.parquet"
    try:
        P02.clean_symbol([raw_file], P02.CLEAN_DIR)
    except Exception:
        logging.exception("[PIPELINE] data_cleaning failed for %s", symbol)

    clean_file = P02.CLEAN_DIR / f"{symbol}_clean.parquet"
    try:
        P03.process_file(clean_file)
    except Exception:
        logging.exception("[PIPELINE] feature_engineering failed for %s", symbol)

    feature_file = P03.FEATURE_DIR / f"{symbol}_feature.parquet"
    try:
        P04.process_file(feature_file)
    except Exception:
        logging.exception("[PIPELINE] labeling failed for %s", symbol)

    label_file = P04.LABEL_DIR / f"{symbol}_label.parquet"
    try:
        P05.process_file(label_file, 0.7, 0.2)
    except Exception:
        logging.exception("[PIPELINE] split failed for %s", symbol)

    try:
        P06.train_and_eval(symbol)
    except Exception:
        logging.exception("[PIPELINE] train failed for %s", symbol)

    try:
        P08.predict_signal(symbol)
    except Exception:
        logging.exception("[PIPELINE] predict failed for %s", symbol)


def _load_model(symbol: str):
    model_path = PIPELINE_ROOT / "ml_data" / "06_models" / f"{symbol}_model.pkl"
    try:
        return joblib.load(model_path)
    except Exception:
        logging.warning("[CHECK] model not found for %s", symbol)
        return None


def check_buy_signal(symbol: str) -> Tuple[bool, bool, bool]:
    """Return ML buy signal and indicator flags for ``symbol``."""
    _ensure_pipeline_modules()

    model = _load_model(symbol)
    if model is None:
        return False, False, False

    df = fetch_ohlcv(symbol, 60)
    if df.empty:
        return False, False, False

    df = _clean_df(df)
    try:
        df = P03.add_features(df)
    except Exception:
        logging.exception("[CHECK] feature engineering failed for %s", symbol)
        return False, False, False

    features = getattr(model, "feature_names_in_", None)
    if features is None:
        features = [c for c in df.columns if c != "timestamp"]
    for f in features:
        if f not in df.columns:
            df[f] = 0
    for col in df.columns:
        if df[col].dtype == "object":
            df[col] = pd.to_numeric(df[col], errors="coerce")
    df.fillna(0, inplace=True)

    last_row = df.iloc[[-1]][list(features)]
    prob = model.predict_proba(last_row)[0][1]
    logging.info("[CHECK] %s prob=%.4f", symbol, prob)
    buy = prob > 0.5

    indicators = f2_buy_indicator.add_basic_indicators(df)
    rsi_flag = bool((indicators["rsi14"].iloc[-1] > 40) & (indicators["rsi14"].iloc[-1] < 60))
    trend_flag = bool(indicators["ema5"].iloc[-1] > indicators["ema20"].iloc[-1])
    return buy, rsi_flag, trend_flag


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
    result = _train_predict(df, symbol)
    cleanup_data_dir()
    return result


def run() -> List[str]:
    logging.info("[RUN] starting buy signal scan")
    logging.info("[SETUP] DATA_ROOT=%s", DATA_ROOT)
    logging.info("[SETUP] MODEL_DIR=%s", MODEL_DIR)
    try:
        with open(CONFIG_DIR / "f5_f1_monitoring_list.json", "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):
            coins = []
            for item in data:
                if isinstance(item, dict):
                    sym = item.get("symbol")
                else:
                    sym = item
                if sym:
                    coins.append(sym)
        else:
            coins = []
        logging.info("[RUN] loaded f5_f1_monitoring_list.json: %s", coins)
    except Exception:
        coins = []
        logging.warning("[RUN] f5_f1_monitoring_list.json missing or invalid")

    buy_list_path = CONFIG_DIR / "f2_f2_realtime_buy_list.json"
    buy_list = load_json(buy_list_path, default=[])
    if not isinstance(buy_list, list):
        buy_list = []
    logging.info("[RUN] existing buy_list=%s", buy_list)
    existing_counts = {}
    pending_set = set()
    for it in buy_list:
        if isinstance(it, dict):
            sym = it.get("symbol")
            if sym:
                existing_counts[sym] = it.get("buy_count", 0)
                if it.get("pending"):
                    pending_set.add(sym)

    pending_path = CONFIG_DIR / "f3_f3_pending_symbols.json"
    pending_set = set(load_json(pending_path, default=[])) if pending_path.exists() else set()
    for it in buy_list:
        if isinstance(it, dict):
            sym = it.get("symbol")
            if sym:
                existing_counts[sym] = it.get("buy_count", 0)

    sell_list_path = CONFIG_DIR / "f3_f3_realtime_sell_list.json"
    sell_list = load_json(sell_list_path, default=[])
    if not isinstance(sell_list, list):
        sell_list = []
    logging.info("[RUN] existing sell_list=%s", sell_list)

    for sym in sell_list:
        existing_counts[sym] = 1

    results = []
    updated: List[dict] = []
    for item in data if isinstance(data, list) else []:
        if isinstance(item, dict):
            sym = item.get("symbol")
            thresh = item.get("thresh_pct")
            loss = item.get("loss_pct")
        else:
            sym = str(item)
            thresh = None
            loss = None
        if not sym:
            continue
        buy, rsi_flag, trend_flag = check_buy_signal(sym)
        logging.info("[%s] buy=%s rsi=%s trend=%s", sym, buy, rsi_flag, trend_flag)
        final = int(buy and rsi_flag and trend_flag)
        updated.append({
            "symbol": sym,
            "ml_signal": int(buy),
            "rsi_sel": int(rsi_flag),
            "trend_sel": int(trend_flag),
            "buy_signal": final,
            "buy_count": existing_counts.get(sym, 0),
            "pending": 1 if sym in pending_set else 0,
        })
        if final:
            results.append(sym)

    save_json(buy_list_path, updated)
    if updated:
        logging.info("[RUN] saved buy_list=%s", updated)
    else:
        logging.info("[RUN] cleared buy_list")
    logging.info("[RUN] finished. %d coins to buy", len(results))
    cleanup_data_dir()
    return results


def run_if_monitoring_list_exists() -> List[str]:
    """Run :func:`run` only when monitoring list is present."""
    path = CONFIG_DIR / "f5_f1_monitoring_list.json"
    if path.exists():
        return run()
    logging.info("[RUN_IF] f5_f1_monitoring_list.json not found; skipping")
    return []


if __name__ == "__main__":
    run_if_monitoring_list_exists()
