import sys
import types
import json
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

if 'smtplib' not in sys.modules:
    smtplib = types.ModuleType('smtplib')
    class DummySMTP:
        def __init__(self, *a, **k):
            pass
        def __enter__(self):
            return self
        def __exit__(self, *a):
            pass
        def starttls(self):
            pass
        def login(self, *a):
            pass
        def sendmail(self, *a, **k):
            pass
    smtplib.SMTP = DummySMTP
    sys.modules['smtplib'] = smtplib

import utils
from helpers.utils.funds import load_fund_settings, save_fund_settings
from helpers.utils.risk import save_risk_settings
import pytest


def test_calc_tis_fallback():
    """get_ticks 실패 시 주문서 정보를 이용한 체결강도 계산을 확인한다."""
    orderbook = [{'total_bid_size': 20, 'total_ask_size': 10}]
    with patch('utils.pyupbit.get_ticks', side_effect=Exception('error')),
         patch('utils.pyupbit.get_orderbook', return_value=orderbook):
        tis = utils.calc_tis('KRW-BTC')
    assert tis == 200.0


def test_load_filter_settings(tmp_path):
    """filter.json이 없거나 잘못되어도 기본값을 반환한다."""
    cfg = utils.load_filter_settings(str(tmp_path / "missing.json"))
    assert cfg["rank"] == 30
    sample = tmp_path / "f.json"
    sample.write_text('{"min_price": 1, "max_price": 2, "rank": 5}', encoding="utf-8")
    cfg2 = utils.load_filter_settings(str(sample))
    assert cfg2 == {"min_price": 1, "max_price": 2, "rank": 5}


def test_fund_settings_io(tmp_path):
    """funds.json 저장 후 재로드를 확인한다."""
    path = tmp_path / "funds.json"
    default = load_fund_settings(str(path))
    assert default["buy_amount"] == 100000
    data = {"max_invest_per_coin": 1000, "buy_amount": 200, "max_concurrent_trades": 2,
            "slippage_tolerance": 0.1, "balance_exhausted_action": "알림"}
    save_fund_settings(data, str(path))
    loaded = load_fund_settings(str(path))
    assert loaded["max_invest_per_coin"] == 1000
    assert loaded["buy_amount"] == 200
    assert "updated" in loaded


def test_fund_settings_validation(tmp_path):
    path = tmp_path / "f.json"
    data = {"max_invest_per_coin": -1, "buy_amount": 1, "max_concurrent_trades": 1,
            "slippage_tolerance": 0.1, "balance_exhausted_action": "알림"}
    with pytest.raises(ValueError):
        save_fund_settings(data, str(path))


def test_risk_settings_validation(tmp_path):
    path = tmp_path / "r.json"
    with pytest.raises(ValueError):
        save_risk_settings({"max_dd_per_coin": -0.1}, str(path))


def test_restore_defaults(tmp_path):
    from helpers.utils.strategy_cfg import (
        restore_defaults,
        load_strategy_list,
        save_strategy_list,
    )
    default_path = tmp_path / "default.json"
    strat_path = tmp_path / "strategy.json"
    backup_path = tmp_path / "backup.json"
    sample = [{"name": "A", "active": False, "buy_condition": "중도적", "sell_condition": "중도적", "priority": 1}]
    sample2 = [{"name": "B"}]
    default_path.write_text(json.dumps(sample, ensure_ascii=False), encoding="utf-8")
    strat_path.write_text(json.dumps(sample2, ensure_ascii=False), encoding="utf-8")
    restore_defaults(str(default_path), str(strat_path), str(backup_path))
    loaded = load_strategy_list(str(strat_path))
    assert loaded == sample
    assert backup_path.exists()


def test_send_email():
    """SMTP 서버 호출 여부를 확인한다."""
    with patch('utils.smtplib.SMTP') as mock_smtp:
        instance = mock_smtp.return_value.__enter__.return_value
        utils.send_email('h', 1, 'u', 'p', 't', 's', 'b')
        mock_smtp.assert_called_with('h', 1, timeout=5)
        instance.starttls.assert_called_once()
        instance.login.assert_called_once_with('u', 'p')
        instance.sendmail.assert_called_once()

