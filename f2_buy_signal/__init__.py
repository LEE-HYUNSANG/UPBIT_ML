"""Lightweight wrapper exposing F2 buy signal utilities."""

from __future__ import annotations

import json
import sys
from importlib import import_module
from pathlib import Path

_submodules = {"01_buy_indicator", "02_ml_buy_signal", "03_buy_signal_engine"}


def __getattr__(name: str):
    if name in _submodules:
        module = import_module(f"f2_ml_buy_signal.{name}")
        sys.modules[f"{__name__}.{name}"] = module
        return module
    raise AttributeError(f"module {__name__} has no attribute {name}")


_STRATEGY_SETTINGS: list | None = None
STRATEGY_SETTINGS_FILE = Path(__file__).resolve().parents[1] / "config" / "app_f2_strategy_settings.json"


def reload_strategy_settings() -> None:
    """Reload F2 strategy settings from :data:`STRATEGY_SETTINGS_FILE`."""

    global _STRATEGY_SETTINGS
    try:
        with open(STRATEGY_SETTINGS_FILE, "r", encoding="utf-8") as f:
            _STRATEGY_SETTINGS = json.load(f)
    except Exception:
        _STRATEGY_SETTINGS = []


def check_signals(symbol: str) -> dict[str, bool]:
    """Return three basic buy signal flags for ``symbol``.

    The function reads the latest prediction CSV produced by the F5 ML
    pipeline and evaluates simple conditions based on that data.  When
    the CSV is missing or cannot be parsed, all flags are returned as
    ``False``.
    """

    pred_path = (
        Path(__file__).resolve().parents[1]
        / "f5_ml_pipeline"
        / "ml_data"
        / "08_pred"
        / f"{symbol}_pred.csv"
    )

    try:
        import pandas as pd

        df = pd.read_csv(pred_path)
    except Exception:
        return {"signal1": False, "signal2": False, "signal3": False}

    if df.empty:
        return {"signal1": False, "signal2": False, "signal3": False}

    last = df.iloc[-1]

    s1 = bool(last.get("buy_signal", 0))

    s2 = False
    try:
        rsi_val = float(last.get("rsi14"))
        s2 = 40 < rsi_val < 60
    except Exception:
        pass

    s3 = False
    try:
        ema5 = float(last.get("ema5"))
        ema20 = float(last.get("ema20"))
        s3 = ema5 > ema20
    except Exception:
        pass

    return {"signal1": s1, "signal2": s2, "signal3": s3}


__all__ = [*list(_submodules), "reload_strategy_settings", "check_signals"]

