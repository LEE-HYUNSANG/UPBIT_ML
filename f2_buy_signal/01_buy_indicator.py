from importlib import import_module as _im
import sys
module = _im('f2_ml_buy_signal.01_buy_indicator')
sys.modules[__name__] = module
