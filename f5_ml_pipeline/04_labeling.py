from __future__ import annotations

import json
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from itertools import product

import numpy as np
import pandas as pd
from numpy.lib.stride_tricks import sliding_window_view

from utils import ensure_dir

PIPELINE_ROOT = Path(__file__).resolve().parent
FEATURE_DIR = PIPELINE_ROOT / "ml_data" / "03_feature"
LABEL_DIR = PIPELINE_ROOT / "ml_data" / "04_label"
LOG_PATH = PIPELINE_ROOT / "logs" / "ml_label.log"

THRESH_LIST      = [0.005, 0.006, 0.007]    # 익절(%)
LOSS_LIST        = [0.005, 0.006, 0.007]    # 손절(%)

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

def make_labels_basic(
    df: pd.DataFrame,
    horizon: int,
    thresh_pct: float,
    loss_pct: float | None = None,
) -> pd.DataFrame:
    """TP/SL만 고려한 라벨 생성 (익절=1, 손절=-1, 관망=0)."""
    if loss_pct is None:
        loss_pct = thresh_pct

    df = df.copy()
    close = df["close"].to_numpy()
    high = df["high"].to_numpy()
    low = df["low"].to_numpy()
    n = len(df)

    labels = np.zeros(n, dtype=int)
    if n <= horizon:
        df["label"] = labels.tolist()
        return df

    windows_high = sliding_window_view(high, horizon + 1)[:, 1:]
    windows_low = sliding_window_view(low, horizon + 1)[:, 1:]
    future_max_high = windows_high.max(axis=1)
    future_min_low = windows_low.min(axis=1)

    entry = close[:-horizon]
    tp = future_max_high >= entry * (1 + thresh_pct)
    sl = future_min_low <= entry * (1 - loss_pct)
    labels[:-horizon] = np.where(tp, 1, np.where(sl, -1, 0))

    df["label"] = labels.tolist()
    return df

def make_labels_trailing(
    df: pd.DataFrame,
    horizon: int,
    thresh_pct: float,
    loss_pct: float,
    trail_start_pct: float,
    trail_down_pct: float,
) -> pd.DataFrame:
    """트레일링스탑 포함 초단타 라벨 생성 (익절=1, 손절=-1, 트레일=2, 관망=0)."""
    if trail_start_pct is None or trail_down_pct is None:
        return make_labels_basic(df, horizon, thresh_pct, loss_pct)

    df = df.copy()
    close = df["close"].to_numpy()
    high = df["high"].to_numpy()
    low = df["low"].to_numpy()
    n = len(df)

    labels = np.zeros(n, dtype=int)
    if n <= horizon:
        df["label"] = labels.tolist()
        return df

    win_high = sliding_window_view(high, horizon + 1)[:, 1:]
    win_low = sliding_window_view(low, horizon + 1)[:, 1:]
    future_high = win_high.max(axis=1)
    future_low = win_low.min(axis=1)
    win_close = sliding_window_view(close, horizon + 1)[:, 1:]
    entry = close[:-horizon]

    tp_mask = future_high >= entry * (1 + thresh_pct)
    sl_mask = future_low <= entry * (1 - loss_pct)
    labels[:-horizon][tp_mask] = 1
    labels[:-horizon][~tp_mask & sl_mask] = -1

    undecided = np.where(~tp_mask & ~sl_mask)[0]
    for idx in undecided:
        prices = win_close[idx]
        ent = entry[idx]
        pct = (prices - ent) / ent
        trigger = np.where(pct >= trail_start_pct)[0]
        if trigger.size:
            t_idx = trigger[0]
            max_price = prices[t_idx]
            for p in prices[t_idx + 1 :]:
                if p > max_price:
                    max_price = p
                drawdown = (p - max_price) / max_price
                if drawdown <= -trail_down_pct:
                    labels[idx] = 2
                    break

    df["label"] = labels.tolist()
    return df

def to_py_types(obj):
    if isinstance(obj, dict):
        return {k: to_py_types(v) for k, v in obj.items()}
    if isinstance(obj, np.integer):
        return int(obj)
    if isinstance(obj, np.floating):
        return float(obj)
    return obj

def optimize_labeling_trailing(
    df: pd.DataFrame,
    symbol: str,
    horizon: int = 5,
) -> dict:
    """트레일링 포함 파라미터 그리드 전체 실험, 최적 조합 자동 선정."""
    results = []
    for thresh, loss in product(THRESH_LIST, LOSS_LIST):
        trail_start, trail_down = None, None
        df_labeled = make_labels_trailing(
            df,
            horizon,
            thresh,
            loss,
            trail_start,
            trail_down,
        )
        n = len(df_labeled)
        n1 = (df_labeled["label"] == 1).sum()
        n2 = (df_labeled["label"] == 2).sum()
        n_1 = (df_labeled["label"] == -1).sum()
        n0 = (df_labeled["label"] == 0).sum()
        ratio_1 = n1 / n
        ratio_2 = n2 / n
        ratio_m1 = n_1 / n
        ratio_0 = n0 / n
        result = {
            "symbol": symbol,
            "thresh_pct": thresh,
            "loss_pct": loss,
            "trail_start_pct": trail_start,
            "trail_down_pct": trail_down,
            "support": ratio_1,
            "row_count": n,
            "label1_count": n1,
            "label2_count": n2,
            "label-1_count": n_1,
            "label0_count": n0
        }
        # ✅ 익절/트레일/손절/관망 비율과 row 수 모두 로그 출력
        ts_start = "None" if trail_start is None else f"{trail_start*100:.2f}%"
        ts_down = "None" if trail_down is None else f"{trail_down*100:.2f}%"
        logging.info(
            "symbol=%s, TP=%.2f%%, SL=%.2f%%, TRAIL=%s/%s | "
            "익절=%.2f%%(%d), 트레일=%.2f%%(%d), 손절=%.2f%%(%d), 관망=%.2f%%(%d), 전체row=%d",
            symbol,
            thresh * 100,
            loss * 100,
            ts_start,
            ts_down,
            ratio_1 * 100,
            n1,
            ratio_2 * 100,
            n2,
            ratio_m1 * 100,
            n_1,
            ratio_0 * 100,
            n0,
            n,
        )
        results.append(result)
    # 0.10~0.20 내에서 0.15에 가장 가까운 조합
    filtered = [r for r in results if 0.10 <= r["support"] <= 0.20]
    if filtered:
        best = min(filtered, key=lambda r: abs(r["support"] - 0.15))
    else:
        best = max(results, key=lambda r: r["support"])
        logging.warning("⚠️ 10%% 미만 support만 나옴! symbol=%s, best=%s", symbol, best)
    return best

def process_file(file: Path, horizon: int = 5) -> None:
    symbol = file.name.split("_")[0]
    try:
        df = pd.read_parquet(file)
    except Exception as exc:
        logging.warning("%s 로드 실패: %s", file.name, exc)
        return

    best_params = optimize_labeling_trailing(df, symbol, horizon)
    df_best = make_labels_trailing(
        df,
        horizon=horizon,
        thresh_pct=best_params["thresh_pct"],
        loss_pct=best_params["loss_pct"],
        trail_start_pct=best_params["trail_start_pct"],
        trail_down_pct=best_params["trail_down_pct"],
    )
    output_path = LABEL_DIR / f"{symbol}_label.parquet"
    try:
        df_best.to_parquet(output_path, index=False)
        dist = df_best["label"].value_counts().to_dict()
        logging.info("[LABEL] %s → %s, shape=%s, dist=%s, best_params=%s",
            file.name, output_path.name, df_best.shape, dist, best_params)
        params_path = LABEL_DIR / f"{symbol}_best_params.json"
        with open(params_path, "w", encoding="utf-8") as f:
            json.dump(to_py_types(best_params), f, indent=2, ensure_ascii=False)
    except Exception as exc:
        logging.warning("%s 저장 실패: %s", output_path.name, exc)

def main() -> None:
    ensure_dir(FEATURE_DIR)
    ensure_dir(LABEL_DIR)
    setup_logger()

    for file in FEATURE_DIR.glob("*.parquet"):
        process_file(file)

# ``tests/test_labeling.py`` expects a ``make_labels`` function.  The
# simplified labeling logic in this project only provides
# ``make_labels_trailing``.  Expose it under the expected name for
# compatibility with the tests and any external callers.
make_labels = make_labels_trailing

if __name__ == "__main__":
    main()
