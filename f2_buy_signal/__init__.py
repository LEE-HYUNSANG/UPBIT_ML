import csv
import logging
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PRED_DIR = PROJECT_ROOT / "f5_ml_pipeline" / "ml_data" / "08_pred"

logger = logging.getLogger(__name__)


def reload_strategy_settings() -> None:
    """Placeholder for compatibility."""
    return None


def check_signals(symbol: str) -> dict:
    """Read prediction file for ``symbol`` and return signal flags."""
    path = PRED_DIR / f"{symbol}_pred.csv"
    result = {"signal1": False, "signal2": False, "signal3": False}
    if not path.exists():
        logger.warning("prediction file not found: %s", path)
        return result
    try:
        with path.open("r", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
    except Exception as exc:
        logger.error("failed to read %s: %s", path, exc)
        return result
    if not rows:
        return result
    row = rows[-1]
    try:
        signal1 = bool(int(float(row.get("buy_signal", row.get("buy_prob", 0)))))
    except Exception:
        try:
            signal1 = float(row.get("buy_prob", 0)) > 0.5
        except Exception:
            signal1 = False
    try:
        rsi = float(row.get("rsi14", 0))
        signal2 = 40 < rsi < 60
    except Exception:
        signal2 = False
    try:
        ema5 = float(row.get("ema5", 0))
        ema20 = float(row.get("ema20", 0))
        signal3 = ema5 > ema20
    except Exception:
        signal3 = False
    result.update(signal1=bool(signal1), signal2=bool(signal2), signal3=bool(signal3))
    return result

__all__ = ["check_signals", "reload_strategy_settings"]
