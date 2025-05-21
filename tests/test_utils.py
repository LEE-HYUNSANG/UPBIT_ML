import sys
import types
from unittest.mock import patch

# 의존 모듈이 없을 때를 대비해 간단한 더미 모듈을 등록한다.
if 'pandas' not in sys.modules:
    pandas = types.ModuleType('pandas')
    pandas.DataFrame = lambda *a, **k: None
    sys.modules['pandas'] = pandas

if 'requests' not in sys.modules:
    requests = types.ModuleType('requests')
    requests.post = lambda *a, **k: None
    sys.modules['requests'] = requests

if 'pyupbit' not in sys.modules:
    pyupbit = types.ModuleType('pyupbit')
    pyupbit.get_ticks = lambda *a, **k: None
    pyupbit.get_orderbook = lambda *a, **k: None
    sys.modules['pyupbit'] = pyupbit

import utils


def test_calc_tis_fallback():
    """get_ticks 실패 시 주문서 정보를 이용한 체결강도 계산을 확인한다."""
    orderbook = [{'total_bid_size': 20, 'total_ask_size': 10}]
    with patch('utils.pyupbit.get_ticks', side_effect=Exception('error')),
         patch('utils.pyupbit.get_orderbook', return_value=orderbook):
        tis = utils.calc_tis('KRW-BTC')
    assert tis == 200.0
