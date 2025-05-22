import json
from app import app, trader, settings


def test_api_post_funds_updates_config(monkeypatch):
    saved = {}

    def fake_save(data, path="config/funds.json"):
        saved.update(data)

    def fake_load(path="config/funds.json"):
        return saved

    monkeypatch.setattr("helpers.utils.funds.save_fund_settings", fake_save)
    monkeypatch.setattr("helpers.utils.funds.load_fund_settings", fake_load)

    client = app.test_client()
    payload = {
        "max_invest_per_coin": 1000,
        "buy_amount": 200,
        "max_concurrent_trades": 3,
        "slippage_tolerance": 0.05,
        "balance_exhausted_action": "알림",
    }
    resp = client.post("/api/funds", json=payload)
    assert resp.status_code == 200
    assert trader.config["amount"] == 200
    assert trader.config["max_positions"] == 3
    assert trader.config["slippage"] == 0.05
    assert settings.buy_amount == 200
    assert settings.max_positions == 3

