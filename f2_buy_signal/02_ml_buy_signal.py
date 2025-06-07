from importlib import import_module as _im
import sys
module = _im('f2_ml_buy_signal.02_ml_buy_signal')
sys.modules[__name__] = module
