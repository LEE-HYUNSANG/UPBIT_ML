"""Simple backtesting using trained and calibrated ML models."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List

try:
    import pandas as pd
    import joblib
    import numpy as np
except ImportError as exc:  # pragma: no cover - runtime import check
    raise SystemExit(
        "This script requires pandas, joblib and numpy. Install them via 'pip install -r requirements.txt'."
    ) from exc

BASE_DIR = Path(__file__).resolve().parent
SPLIT_DIR = BASE_DIR / "ml_data/05_split"
MODEL_DIR = BASE_DIR / "ml_data/06_models"
METRIC_DIR = BASE_DIR / "ml_data/08_metrics"
METRIC_DIR.mkdir(parents=True, exist_ok=True)


def _detect_time_column(df: pd.DataFrame) -> str | None:
    """Return the name of the timestamp column if present."""
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


def _detect_label_pairs(df: pd.DataFrame) -> List[str]:
    """Return strategy codes that have both buy and sell labels."""
    buys = {c[len("buy_label_"):] for c in df.columns if c.startswith("buy_label_")}
    sells = {c[len("sell_label_"):] for c in df.columns if c.startswith("sell_label_")}
    return sorted(buys & sells)


def _prepare_X(df: pd.DataFrame, label_cols: List[str]) -> pd.DataFrame:
    """Drop label columns and non numeric features."""
    X = df.drop(columns=label_cols, errors="ignore")
    for col in X.columns:
        if not pd.api.types.is_numeric_dtype(X[col]):
            X = X.drop(columns=[col])
    return X.fillna(0)


def _load_model_parts(symbol: str, label: str):
    """Load model, calibration object and threshold for ``label``."""
    model_path = MODEL_DIR / f"{symbol}_{label}_model.pkl"
    calib_path = MODEL_DIR / f"{symbol}_{label}_calib.pkl"
    thresh_path = MODEL_DIR / f"{symbol}_{label}_thresh.json"
    if not (model_path.exists() and calib_path.exists() and thresh_path.exists()):
        print(f"Model artifacts missing for {symbol} {label}")
        return None, None, None
    model = joblib.load(model_path)
    calib = joblib.load(calib_path)
    with thresh_path.open() as f:
        thresh = json.load(f).get("threshold", 0.5)
    return model, calib, thresh


def _simulate_trades(
    df: pd.DataFrame,
    buy_probs: List[float],
    sell_probs: List[float],
    buy_thresh: float,
    sell_thresh: float,
    time_col: str,
) -> List[Dict[str, float]]:
    """Generate trade records using threshold based signals."""

    trades: List[Dict[str, float]] = []
    position: Dict[str, float] | None = None

    for i in range(len(df)):
        price = df.iloc[i]["close"]
        ts = df.iloc[i][time_col]

        if position is None and buy_probs[i] >= buy_thresh:
            position = {"entry_time": ts, "entry_price": price}
            continue

        if position and sell_probs[i] >= sell_thresh:
            exit_price = price
            ret = (exit_price - position["entry_price"]) / position["entry_price"]
            trades.append(
                {
                    "entry_time": position["entry_time"],
                    "exit_time": ts,
                    "entry_price": position["entry_price"],
                    "exit_price": exit_price,
                    "return": ret,
                }
            )
            position = None

    if position is not None:
        exit_price = df.iloc[-1]["close"]
        ts = df.iloc[-1][time_col]
        ret = (exit_price - position["entry_price"]) / position["entry_price"]
        trades.append(
            {
                "entry_time": position["entry_time"],
                "exit_time": ts,
                "entry_price": position["entry_price"],
                "exit_price": exit_price,
                "return": ret,
            }
        )

    return trades


def _compute_kpis(trades: List[Dict[str, float]]) -> Dict[str, float]:
    """Return basic KPI metrics for ``trades``."""

    if not trades:
        return {
            "ROI": 0.0,
            "WinRate": 0.0,
            "MDD": 0.0,
            "Sharpe": 0.0,
            "Trades": 0,
        }

    rets = np.array([t["return"] for t in trades])
    equity = np.cumprod(1 + rets)
    peak = np.maximum.accumulate(equity)
    drawdown = (equity - peak) / peak

    roi = equity[-1] - 1
    winrate = float(np.mean(rets > 0))
    mdd = float(drawdown.min())
    sharpe = float(0.0)
    if rets.std(ddof=1) > 0:
        sharpe = float(np.sqrt(len(rets)) * rets.mean() / rets.std(ddof=1))

    return {
        "ROI": roi * 100,
        "WinRate": winrate * 100,
        "MDD": mdd * 100,
        "Sharpe": sharpe,
        "Trades": len(trades),
    }


def backtest_symbol(test_path: Path) -> None:
    """Backtest all strategy label pairs for a single symbol."""

    symbol = test_path.stem.replace("_test", "")
    print(f"Backtesting {symbol}")

    try:
        df = pd.read_parquet(test_path)
    except Exception as err:
        print(f"Failed to load {test_path.name}: {err}")
        return

    time_col = _detect_time_column(df)
    if not time_col or "close" not in df.columns:
        print(f"Missing required columns in {test_path.name}")
        return

    strategies = _detect_label_pairs(df)
    if not strategies:
        print(f"No label pairs found for {symbol}")
        return

    for strat in strategies:
        buy_label = f"buy_label_{strat}"
        sell_label = f"sell_label_{strat}"

        buy_model, buy_calib, buy_thresh = _load_model_parts(symbol, buy_label)
        sell_model, sell_calib, sell_thresh = _load_model_parts(symbol, sell_label)
        if not all([buy_model, buy_calib, sell_model, sell_calib]):
            continue

        X = _prepare_X(df, [buy_label, sell_label])
        buy_probs_raw = buy_model.predict_proba(X)[:, 1]
        sell_probs_raw = sell_model.predict_proba(X)[:, 1]
        buy_probs = buy_calib.predict(buy_probs_raw)
        sell_probs = sell_calib.predict(sell_probs_raw)

        trades = _simulate_trades(df, buy_probs, sell_probs, buy_thresh, sell_thresh, time_col)
        summary = _compute_kpis(trades)

        trades_df = pd.DataFrame(trades)
        trades_csv = METRIC_DIR / f"{symbol}_{strat}_trades.csv"
        trades_df.to_csv(trades_csv, index=False)

        summary_path = METRIC_DIR / f"{symbol}_{strat}_backtest_summary.json"
        with summary_path.open("w") as f:
            json.dump(summary, f, indent=2)

        print(
            f"{symbol} {strat}: ROI={summary['ROI']:.2f}% "
            f"Trades={summary['Trades']} WinRate={summary['WinRate']:.2f}%"
        )


def main() -> None:
    if not SPLIT_DIR.exists():
        print(f"Split directory {SPLIT_DIR} missing")
        return

    test_files = list(SPLIT_DIR.glob("*_test.parquet"))
    if not test_files:
        print(f"No test files found in {SPLIT_DIR}")
        return

    for test_path in test_files:
        backtest_symbol(test_path)


if __name__ == "__main__":
    main()


