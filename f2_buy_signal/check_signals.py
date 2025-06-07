from __future__ import annotations

from pathlib import Path
import csv

PRED_DIR = Path(__file__).resolve().parents[1] / "f5_ml_pipeline" / "ml_data" / "08_pred"


def _to_bool(value) -> bool:
    try:
        return bool(int(float(value)))
    except Exception:
        return bool(value)


def check_signals(symbol: str) -> dict[str, bool]:
    """Return the latest ML signals for ``symbol``.

    Parameters
    ----------
    symbol : str
        Market code such as ``KRW-BTC``.

    Returns
    -------
    dict[str, bool]
        Dictionary with ``signal1``, ``signal2`` and ``signal3`` flags. If the
        prediction file is missing or malformed all values are ``False``.
    """
    path = PRED_DIR / f"{symbol}_pred.csv"
    try:
        with open(path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            last = None
            for row in reader:
                last = row
            if not last:
                raise ValueError("empty file")
            return {
                "signal1": _to_bool(last.get("signal1")),
                "signal2": _to_bool(last.get("signal2")),
                "signal3": _to_bool(last.get("signal3")),
            }
    except Exception:
        return {"signal1": False, "signal2": False, "signal3": False}
