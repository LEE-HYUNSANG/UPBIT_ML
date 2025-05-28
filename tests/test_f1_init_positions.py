import os
import json
import sys
import types

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

if 'requests' not in sys.modules:
    sys.modules['requests'] = types.SimpleNamespace()

from f1_universe.universe_selector import init_coin_positions

class DummyClient:
    def get_accounts(self):
        return [
            {"currency": "XRP", "balance": "10", "avg_buy_price": "500", "unit_currency": "KRW"},
            {"currency": "ETH", "balance": "0.001", "avg_buy_price": "1000000", "unit_currency": "KRW"},
        ]

def test_init_coin_positions(tmp_path, monkeypatch):
    out = tmp_path / "pos.json"
    monkeypatch.setattr("f3_order.upbit_api.UpbitClient", lambda: DummyClient())
    init_coin_positions(threshold=3000, path=str(out))
    with open(out, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert len(data) == 1
    assert data[0]["symbol"] == "KRW-XRP"
    assert data[0]["origin"] == "imported"
