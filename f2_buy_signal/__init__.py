from importlib import import_module
import sys

_submodules = {"01_buy_indicator", "02_ml_buy_signal", "03_buy_signal_engine"}

def __getattr__(name):
    if name in _submodules:
        module = import_module(f"f2_ml_buy_signal.{name}")
        sys.modules[f"{__name__}.{name}"] = module
        return module
    raise AttributeError(f"module {__name__} has no attribute {name}")

__all__ = list(_submodules)
