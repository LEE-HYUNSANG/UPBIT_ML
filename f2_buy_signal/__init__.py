from importlib import import_module
import sys

_submodules = {"01_buy_indicator", "02_ml_buy_signal", "03_buy_signal_engine"}
from .check_signals import check_signals


def reload_strategy_settings() -> None:
    """Placeholder for runtime strategy reload."""
    return None

def __getattr__(name):
    if name in _submodules:
        module = import_module(f"f2_ml_buy_signal.{name}")
        sys.modules[f"{__name__}.{name}"] = module
        return module
    raise AttributeError(f"module {__name__} has no attribute {name}")

__all__ = list(_submodules) + ["check_signals", "reload_strategy_settings"]
