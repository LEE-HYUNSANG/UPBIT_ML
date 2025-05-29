import json
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from f1_universe import universe_selector as us


def test_load_selected_universe_extracts_symbols(tmp_path):
    data = [
        {"symbol": "KRW-BTC", "win_rate": 0.6},
        {"symbol": "KRW-ETH"},
        {"no_symbol": "KRW-XRP"},
    ]
    f = tmp_path / "strategies.json"
    f.write_text(json.dumps(data, ensure_ascii=False))
    result = us.load_selected_universe(str(f))
    assert result == ["KRW-BTC", "KRW-ETH"]


def test_load_monitoring_coins(tmp_path):
    coins = ["KRW-BTC", "KRW-ETH"]
    f = tmp_path / "mon.json"
    f.write_text(json.dumps(coins, ensure_ascii=False))
    result = us.load_monitoring_coins(str(f))
    assert result == coins


def test_select_universe_prefers_monitoring(monkeypatch):
    monkeypatch.setattr(us, "load_monitoring_coins", lambda path=None: ["KRW-BTC"])
    monkeypatch.setattr(us, "load_selected_universe", lambda path=None: ["KRW-ETH"])
    monkeypatch.setattr(us, "load_universe_from_file", lambda path=None: ["KRW-XRP"])
    assert us.select_universe() == ["KRW-BTC"]
