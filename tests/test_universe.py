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
