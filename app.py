from flask import Flask, Response, render_template, jsonify, request
import json
import sqlite3
import os
import uuid
import jwt
import requests
import datetime
import logging
from logging.handlers import RotatingFileHandler
from signal_loop import process_symbol, main_loop
from f1_universe.universe_selector import (
    select_universe,
    load_config,
    get_universe,
    schedule_universe_updates,
    update_universe,
    load_universe_from_file,
    CONFIG_PATH,
)

app = Flask(__name__)

CONFIG = load_config()
load_universe_from_file()
schedule_universe_updates(1800, CONFIG)

CFG_DIR = "config/setting_date"
LATEST_CFG = os.path.join(CFG_DIR, "Latest_config.json")
DEFAULT_CFG = os.path.join(CFG_DIR, "default_config.json")
ML_CFG = os.path.join(CFG_DIR, "ML_config.json")
YDAY_CFG = os.path.join(CFG_DIR, "yesterday_config.json")

RISK_CONFIG_PATH = LATEST_CFG

AUTOTRADE_STATUS_FILE = os.path.join("config", "autotrade_status.json")
EVENTS_LOG = os.path.join("logs", "events.jsonl")


def load_risk_config(path: str = RISK_CONFIG_PATH) -> dict:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}


def save_risk_config(data: dict, path: str = RISK_CONFIG_PATH) -> None:
    cfg = load_risk_config(path)
    cfg.update(data)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2, ensure_ascii=False)


def load_auto_trade_status() -> dict:
    try:
        with open(AUTOTRADE_STATUS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {"enabled": False, "updated_at": ""}


def save_auto_trade_status(data: dict) -> None:
    os.makedirs(os.path.dirname(AUTOTRADE_STATUS_FILE), exist_ok=True)
    with open(AUTOTRADE_STATUS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def load_recent_events(limit: int = 20) -> list:
    if not os.path.exists(EVENTS_LOG):
        return []
    with open(EVENTS_LOG, "r", encoding="utf-8") as f:
        lines = f.readlines()[-limit:]
    events = []
    for line in lines:
        try:
            events.append(json.loads(line))
        except Exception:
            continue
    return events


def get_config_path(name: str) -> str:
    """Return full path for a named config set."""
    mapping = {
        "latest": LATEST_CFG,
        "default": DEFAULT_CFG,
        "ml": ML_CFG,
        "yesterday": YDAY_CFG,
    }
    return mapping.get(name, LATEST_CFG)


WEB_LOGGER = None
if WEB_LOGGER is None:
    WEB_LOGGER = logging.getLogger("web")
    os.makedirs("logs", exist_ok=True)
    handler = RotatingFileHandler(
        "logs/web.log",
        encoding="utf-8",
        maxBytes=100_000 * 1024,
        backupCount=1000,
    )
    handler.setFormatter(
        logging.Formatter("%(asctime)s [WEB] %(levelname)s %(message)s")
    )
    WEB_LOGGER.addHandler(handler)
    WEB_LOGGER.setLevel(logging.INFO)


from f3_order.utils import load_api_keys


def fetch_account_info() -> dict:
    """Fetch KRW balance and today's PnL from Upbit.

    The function uses a JWT token to authenticate with the Upbit API. If the
    request fails, ``0`` values are returned.
    """

    access_key, secret_key = load_api_keys()
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
    pnl = 0.0
    try:
        params = {"state": "done", "page": 1, "order_by": "desc"}
        resp = requests.get("https://api.upbit.com/v1/orders", headers=headers, params=params, timeout=10)
        resp.raise_for_status()
        orders = resp.json()
        today = datetime.date.today()
        for o in orders:
            t = datetime.datetime.fromisoformat(o.get("created_at", "").replace("Z", "+00:00")).astimezone().date()
            if t != today:
                continue
            pnl += float(o.get("paid_fee", 0)) * -1
    except Exception:
        pnl = 0.0
    return {"krw_balance": krw_balance, "pnl": pnl}


@app.route("/api/account")
def api_account() -> Response:
    """Return account info as JSON."""
    return jsonify(fetch_account_info())


@app.route("/api/signals")
def api_signals() -> Response:
    """Return F2 signal results for the current universe."""
    universe = get_universe()
    if not universe:
        universe = select_universe(CONFIG)
    results = {}
    for ticker in universe:
        data = process_symbol(ticker)
        if data:
            results[ticker] = data
    return jsonify(results)


@app.route("/api/universe_config", methods=["GET", "POST"])
def universe_config_endpoint() -> Response:
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


@app.route("/api/risk_config", methods=["GET", "POST"])
def risk_config_endpoint() -> Response:
    """Get or update risk management configuration."""
    if request.method == "GET":
        src = request.args.get("source", "latest")
        path = get_config_path(src)
        cfg = load_risk_config(path)
        if not cfg and src == "latest":
            cfg = load_risk_config(DEFAULT_CFG)
        return jsonify(cfg)

    data = request.get_json(force=True) or {}
    save_risk_config(data, LATEST_CFG)
    WEB_LOGGER.info(f"Risk config updated: {data}")
    return jsonify({"status": "ok"})


@app.route("/api/auto_trade_status", methods=["GET", "POST"])
def auto_trade_status_endpoint() -> Response:
    """Get or update the auto trading enabled state."""
    if request.method == "GET":
        return jsonify(load_auto_trade_status())
    data = request.get_json(force=True) or {}
    enabled = bool(data.get("enabled", False))
    status = {
        "enabled": enabled,
        "updated_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }
    save_auto_trade_status(status)
    return jsonify({"success": True, **status})


@app.route("/api/open_positions")
def open_positions_endpoint() -> Response:
    """Return currently open positions managed by the order executor."""
    from f3_order.order_executor import _default_executor

    positions = [
        p
        for p in _default_executor.position_manager.positions
        if p.get("status") == "open"
    ]
    return jsonify(positions)


@app.route("/api/events")
def events_endpoint() -> Response:
    """Return recent application events."""
    limit = int(request.args.get("limit", 20))
    return jsonify(load_recent_events(limit))


@app.route("/api/risk_events")
def risk_events_endpoint() -> Response:
    """Return recent risk manager events from the SQLite log."""
    db_path = os.path.join("logs", "risk_events.db")
    if not os.path.exists(db_path):
        return jsonify([])
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("SELECT timestamp, state, message FROM risk_events ORDER BY timestamp DESC LIMIT 100")
    rows = cur.fetchall()
    conn.close()
    events = [
        {"timestamp": ts, "state": st, "message": msg}
        for ts, st, msg in rows
    ]
    return jsonify(events)

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
    # When running this file directly, also launch the signal processing loop
    # in a background thread so signals continue to be evaluated.
    import threading

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [F1F2] [%(levelname)s] %(message)s",
        handlers=[
            RotatingFileHandler(
                "logs/F1F2_loop.log",
                encoding="utf-8",
                maxBytes=100_000 * 1024,
                backupCount=1000,
            ),
            RotatingFileHandler(
                "logs/F1_signal_engine.log",
                encoding="utf-8",
                maxBytes=100_000 * 1024,
                backupCount=1000,
            ),
            RotatingFileHandler(
                "logs/F2_signal_engine.log",
                encoding="utf-8",
                maxBytes=100_000 * 1024,
                backupCount=1000,
            ),
            logging.StreamHandler(),
        ],
        force=True,
    )

    thread = threading.Thread(target=main_loop, daemon=True)
    thread.start()

    # Run the Flask development server. Set host to "0.0.0.0" so the app is reachable via localhost.
    app.run(host="0.0.0.0", port=5000, debug=True)
