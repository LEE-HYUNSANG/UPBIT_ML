"""예측 결과와 라벨을 사용해 간단한 백테스트를 수행한다."""

from __future__ import annotations

import json
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

import numpy as np
import pandas as pd

from utils import ensure_dir

PRED_DIR = Path("ml_data/08_pred")
LABEL_DIR = Path("ml_data/04_label")
OUT_DIR = Path("ml_data/09_backtest")
LOG_PATH = Path("logs/ml_backtest.log")
COMMISSION = 0.001  # 0.1% upbit round trip


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


def simulate_exit(df: pd.DataFrame, start_idx: int, params: dict) -> tuple[int, float, str]:
    """TP/SL/TS 중 먼저 충족되는 시점과 가격을 반환."""
    tp_pct = params.get("thresh_pct", 0)
    sl_pct = params.get("loss_pct", 0)
    ts_start = params.get("trail_start_pct", 0)
    ts_down = params.get("trail_down_pct", 0)

    entry = df.iloc[start_idx].get("close", df.iloc[start_idx].get("close_pred"))
    tp_price = entry * (1 + tp_pct)
    sl_price = entry * (1 - sl_pct)

    trail_active = False
    highest = entry

    for i in range(start_idx + 1, len(df)):
        row = df.iloc[i]
        close = row.get("close", row.get("close_pred"))
        high = row.get("high", close)
        low = row.get("low", close)

        if high >= tp_price:
            return i, tp_price, "TP"

        if low <= sl_price:
            return i, sl_price, "SL"

        roi = (close - entry) / entry
        if not trail_active and roi >= ts_start:
            trail_active = True
            highest = close
        elif trail_active:
            if close > highest:
                highest = close
            if (close - highest) / highest <= -ts_down:
                return i, close, "TS"

    final_close = df.iloc[-1].get("close", df.iloc[-1].get("close_pred"))
    return len(df) - 1, final_close, "FORCE"


def summarize(rois: pd.Series) -> tuple[float, float]:
    """Sharpe ratio와 MDD 계산."""
    sharpe = 0.0
    if len(rois) > 1 and rois.std(ddof=0) != 0:
        sharpe = rois.mean() / rois.std(ddof=0) * np.sqrt(len(rois))
    equity = (1 + rois).cumprod()
    running_max = equity.cummax()
    drawdown = (equity - running_max) / running_max
    mdd = float(drawdown.min()) if not drawdown.empty else 0.0
    return float(sharpe), mdd


def process_symbol(symbol: str) -> None:
    """단일 심볼의 백테스트 수행."""
    pred_path = PRED_DIR / f"{symbol}_pred.csv"
    label_path = LABEL_DIR / f"{symbol}_label.parquet"
    params_path = LABEL_DIR / f"{symbol}_best_params.json"

    try:
        pred_df = pd.read_csv(pred_path)
        label_df = pd.read_parquet(label_path)
        with open(params_path, "r", encoding="utf-8") as f:
            params = json.load(f)
        if "timestamp" in pred_df.columns:
            pred_df["timestamp"] = pd.to_datetime(pred_df["timestamp"], utc=True)
            pred_df["timestamp"] = pred_df["timestamp"].dt.tz_localize(None)
        if "timestamp" in label_df.columns:
            label_df["timestamp"] = pd.to_datetime(label_df["timestamp"], utc=True)
            label_df["timestamp"] = label_df["timestamp"].dt.tz_localize(None)
    except Exception as exc:  # pragma: no cover - best effort
        logging.warning("%s 로드 실패: %s", symbol, exc)
        return

    if "label" not in label_df.columns:
        label_cols = ["timestamp"]
    else:
        label_cols = ["timestamp", "label"]
    price_cols = [c for c in ["open", "high", "low", "close"] if c in label_df.columns]
    df = pd.merge(
        pred_df,
        label_df[label_cols + price_cols],
        on="timestamp",
        how="inner",
        suffixes=("_pred", ""),
    )
    for col in ["open", "high", "low", "close"]:
        pred_col = f"{col}_pred"
        if col not in df.columns and pred_col in df.columns:
            df.rename(columns={pred_col: col}, inplace=True)
    if df.empty:
        logging.warning("%s 정합성 문제: 병합 결과 0 rows", symbol)
        return

    trades = []
    i = 0
    while i < len(df):
        row = df.iloc[i]
        if row.get("buy_signal") == 1:
            exit_idx, exit_price, result = simulate_exit(df, i, params)
            entry_price = row["close"]
            gross = exit_price / entry_price - 1
            net = gross - COMMISSION
            trades.append({
                "timestamp": row["timestamp"],
                "entry_price": entry_price,
                "result": result,
                "exit_time": df.iloc[exit_idx]["timestamp"],
                "exit_price": exit_price,
                "gross_roi": gross,
                "net_roi": net,
            })
            i = exit_idx + 1
        else:
            i += 1

    if not trades:
        logging.info("[BACKTEST] %s 매매 없음", symbol)
        return

    trades_df = pd.DataFrame(trades)
    tp = (trades_df["result"] == "TP").sum()
    trail = (trades_df["result"] == "TS").sum()
    sl = (trades_df["result"] == "SL").sum()
    hold = 0
    force = (trades_df["result"] == "FORCE").sum()
    win = tp + trail
    total = len(trades_df)

    sharpe, mdd = summarize(trades_df["net_roi"])

    summary = {
        "total_entries": total,
        "tp_count": int(tp),
        "trail_count": int(trail),
        "sl_count": int(sl),
        "hold_count": int(hold),
        "force_count": int(force),
        "win_rate": float(win / total) if total else 0.0,
        "loss_rate": float(sl / total) if total else 0.0,
        "avg_roi": float(trades_df["net_roi"].mean()),
        "cum_roi": float(trades_df["net_roi"].sum()),
        "sharpe": sharpe,
        "mdd": mdd,
        "avg_roi_gross": float(trades_df["gross_roi"].mean()),
        "cum_roi_gross": float(trades_df["gross_roi"].sum()),
    }

    ensure_dir(OUT_DIR)
    trades_path = OUT_DIR / f"{symbol}_trades.csv"
    summary_path = OUT_DIR / f"{symbol}_summary.json"
    trades_df.to_csv(trades_path, index=False)
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    logging.info(
        "[BACKTEST] %s entries=%d win_rate=%.2f%% avg_roi=%.4f sharpe=%.2f mdd=%.2f%%",
        symbol,
        total,
        summary["win_rate"] * 100,
        summary["avg_roi"],
        summary["sharpe"],
        summary["mdd"] * 100,
    )


def main() -> None:
    """실행 엔트리 포인트."""
    ensure_dir(PRED_DIR)
    ensure_dir(LABEL_DIR)
    ensure_dir(OUT_DIR)
    setup_logger()

    for file in PRED_DIR.glob("*_pred.csv"):
        symbol = file.stem.split("_")[0]
        process_symbol(symbol)


if __name__ == "__main__":
    main()
