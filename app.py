from flask import Flask, render_template, jsonify, request
import json
import os
import uuid
import jwt
import requests
from f1_universe import (
    select_universe,
    load_config,
    get_universe,
    schedule_universe_updates,
    update_universe,
    CONFIG_PATH,
)

app = Flask(__name__)

CONFIG = load_config()
schedule_universe_updates(1800, CONFIG)


def _load_api_keys(path: str = ".env.json") -> tuple[str, str]:
    """Return Upbit API access and secret keys from the JSON env file."""
    if not os.path.exists(path):
        return "", ""
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data.get("UPBIT_KEY", ""), data.get("UPBIT_SECRET", "")


def fetch_account_info() -> dict:
    """Fetch KRW balance and today's PnL from Upbit.

    The function uses a JWT token to authenticate with the Upbit API. If the
    request fails, ``0`` values are returned.
    """

    access_key, secret_key = _load_api_keys()
    if not access_key or not secret_key:
        return {"krw_balance": 0, "pnl": 0}

    payload = {"access_key": access_key, "nonce": str(uuid.uuid4())}
    token = jwt.encode(payload, secret_key)
    headers = {"Authorization": f"Bearer {token}"}

    try:
        response = requests.get("https://api.upbit.com/v1/accounts", headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()
        krw_balance = 0.0
        for item in data:
            if item.get("currency") == "KRW":
                krw_balance = float(item.get("balance", 0))
                break
    except Exception:
        krw_balance = 0.0

    # TODO: Calculate today's PnL using trade history
    pnl = 0.0
    return {"krw_balance": krw_balance, "pnl": pnl}


@app.route("/api/account")
def api_account() -> "Response":
    """Return account info as JSON."""
    return jsonify(fetch_account_info())


@app.route("/api/universe_config", methods=["GET", "POST"])
def universe_config_endpoint() -> "Response":
    """Get or update universe filter configuration."""
    if request.method == "GET":
        cfg = load_config()
        return jsonify(
            {
                "min_price": cfg.get("min_price", 0),
                "max_price": cfg.get("max_price", float("inf")),
                "min_volatility": cfg.get("min_volatility", 0.0),
                "volume_rank": cfg.get("volume_rank", 50),
            }
        )

    data = request.get_json(force=True) or {}
    cfg = load_config()
    cfg["min_price"] = float(data.get("min_price", cfg.get("min_price", 0)))
    cfg["max_price"] = float(data.get("max_price", cfg.get("max_price", 0)))
    cfg["min_volatility"] = float(
        data.get("min_volatility", cfg.get("min_volatility", 0.0))
    )
    cfg["volume_rank"] = int(data.get("volume_rank", cfg.get("volume_rank", 50)))

    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2)

    CONFIG.update(cfg)
    update_universe(CONFIG)
    return jsonify({"status": "ok", "universe": get_universe()})

@app.route("/")
def home():
    """Root page showing the current trading universe."""
    universe = get_universe()
    if not universe:
        universe = select_universe(CONFIG)
    return render_template("index.html", universe=universe)


@app.route("/dashboard")
def dashboard():
    """Render the main dashboard page."""
    universe = get_universe()
    if not universe:
        universe = select_universe(CONFIG)
    return render_template("01_Home.html", universe=universe, config=CONFIG)


@app.route("/strategy")
def strategy():
    """Render the strategy configuration page."""
    return render_template("02_Strategy.html")


@app.route("/risk")
def risk():
    """Render the risk management page."""
    return render_template("03_Risk.html")


@app.route("/analysis")
def analysis():
    """Render the data analysis page."""
    return render_template("04_Analysis.html")


@app.route("/settings")
def settings():
    """Render the personal settings page."""
    return render_template("05_pSettings.html")


if __name__ == "__main__":
    # Run the Flask development server when executing this file directly.
    # Set host to "0.0.0.0" so the app is reachable via localhost.
    app.run(host="0.0.0.0", port=5000, debug=True)
