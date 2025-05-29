from flask import Flask, Response, render_template, jsonify, request
import json
import sqlite3
import os
import uuid
import jwt
import requests
import datetime
import time
import logging
from logging.handlers import RotatingFileHandler
from signal_loop import process_symbol, main_loop
import threading
from f1_universe.universe_selector import (
    select_universe,
    load_config,
    get_universe,
    schedule_universe_updates,
    update_universe,
    load_universe_from_file,
    CONFIG_PATH,
)
from f2_signal.signal_engine import reload_strategy_settings

app = Flask(__name__)
PORT = int(os.environ.get("PORT", 3000))

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

STRATEGY_SETTINGS_FILE = os.path.join("config", "strategy_settings.json")
STRATEGY_YDAY_FILE = os.path.join("config", "strategy_settings_yesterday.json")
STRATEGIES_MASTER_FILE = "strategies_master_pruned.json"

# 자동 매매 스레드의 실행 상태 보관용 변수
_auto_trade_thread = None
_auto_trade_stop = None
_monitor_thread = None
_monitor_stop = None


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


def load_strategy_master() -> list:
    with open(STRATEGIES_MASTER_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def load_strategy_settings(path: str = STRATEGY_SETTINGS_FILE) -> list:
    master = load_strategy_master()
    defaults = {
        s["short_code"]: {"short_code": s["short_code"], "on": True, "order": i + 1}
        for i, s in enumerate(master)
    }
    if path and os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            settings = json.load(f)
        existing = {s.get("short_code") for s in settings}
        for code, val in defaults.items():
            if code not in existing:
                settings.append(val)
        return settings
    return list(defaults.values())


def save_strategy_settings(data: list, path: str = STRATEGY_SETTINGS_FILE) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def start_auto_trade() -> None:
    """백그라운드 스레드에서 자동 매매 루프 시작"""
    global _auto_trade_thread, _auto_trade_stop
    if _auto_trade_thread and _auto_trade_thread.is_alive():
        return
    _auto_trade_stop = threading.Event()
    _auto_trade_thread = threading.Thread(
        target=main_loop,
        kwargs={"stop_event": _auto_trade_stop},
        daemon=True,
    )
    _auto_trade_thread.start()
    stop_monitoring()


def stop_auto_trade() -> None:
    """실행 중인 자동 매매 루프 중지"""
    global _auto_trade_thread, _auto_trade_stop
    if _auto_trade_stop:
        _auto_trade_stop.set()
    _auto_trade_thread = None
    start_monitoring()


def start_monitoring() -> None:
    """신규 진입 없이 위험 모니터링 루프 실행"""
    global _monitor_thread, _monitor_stop
    if _monitor_thread and _monitor_thread.is_alive():
        return
    from signal_loop import RiskManager, _default_executor  # lazy import
    _monitor_stop = threading.Event()

    def monitor_worker():
        rm = RiskManager(
            order_executor=_default_executor,
            exception_handler=_default_executor.exception_handler,
        )
        _default_executor.set_risk_manager(rm)
        while not _monitor_stop.is_set():
            open_syms = [
                p.get("symbol")
                for p in _default_executor.position_manager.positions
                if p.get("status") == "open"
            ]
            rm.update_account(0.0, 0.0, 0.0, open_syms)
            rm.periodic()
            _default_executor.manage_positions()
            time.sleep(1)

    _monitor_thread = threading.Thread(target=monitor_worker, daemon=True)
    _monitor_thread.start()


def stop_monitoring() -> None:
    global _monitor_thread, _monitor_stop
    if _monitor_stop:
        _monitor_stop.set()
    _monitor_thread = None


def get_config_path(name: str) -> str:
    """설정 이름에 해당하는 파일 경로 반환"""
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
from f3_order.upbit_api import UpbitClient


def fetch_account_info() -> dict:
    """업비트에서 KRW 잔고와 당일 손익을 조회합니다.

    JWT 토큰 인증을 사용하며 실패 시 0을 반환합니다.
    """

    access_key, secret_key = load_api_keys()
    if not access_key or not secret_key:
        return {"krw_balance": 0.0, "pnl": 0.0}

    client = UpbitClient(access_key, secret_key)

    try:
        accounts = client.get_accounts()
        krw_balance = 0.0
        for item in accounts:
            if item.get("currency") == "KRW":
                krw_balance = float(item.get("balance", 0))
                break
    except Exception:
        krw_balance = 0.0

    pnl = 0.0
    try:
        params = {"state": "done", "page": 1, "order_by": "desc"}
        orders = client.orders(params)
        today = datetime.date.today()
        for o in orders:
            t = (
                datetime.datetime.fromisoformat(o.get("created_at", "").replace("Z", "+00:00"))
                .astimezone()
                .date()
            )
            if t != today:
                continue
            pnl += float(o.get("paid_fee", 0)) * -1
    except Exception:
        pnl = 0.0
    return {"krw_balance": krw_balance, "pnl": pnl}


@app.route("/api/account")
def api_account() -> Response:
    """계좌 정보를 JSON 형태로 반환"""
    return jsonify(fetch_account_info())


@app.route("/api/signals")
def api_signals() -> Response:
    """현재 유니버스에 대한 F2 신호 결과 반환"""
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
    """유니버스 필터 설정 조회 또는 업데이트"""
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
    """위험 관리 설정을 조회하거나 갱신"""
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
    """자동 매매 활성화 상태 조회/변경"""
    if request.method == "GET":
        return jsonify(load_auto_trade_status())
    data = request.get_json(force=True) or {}
    enabled = bool(data.get("enabled", False))
    status = {
        "enabled": enabled,
        "updated_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }
    save_auto_trade_status(status)
    if enabled:
        start_auto_trade()
    else:
        stop_auto_trade()
    return jsonify({"success": True, **status})


@app.route("/api/open_positions")
def open_positions_endpoint() -> Response:
    """주문 실행기로부터 열린 포지션 목록을 반환합니다.

    항상 JSON 배열을 반환하며, 포지션이 없을 경우 ``[]``를 돌려줍니다.
    """
    from f3_order.order_executor import _default_executor
    pm = _default_executor.position_manager
    pm.refresh_positions()
    positions = [
        p
        for p in pm.positions
        if p.get("status") == "open"
    ]
    # 열린 포지션이 없을 때는 빈 배열을 명시적으로 반환
    return jsonify(positions if positions else [])


@app.route("/api/events")
def events_endpoint() -> Response:
    """최근 애플리케이션 이벤트 조회"""
    limit = int(request.args.get("limit", 20))
    return jsonify(load_recent_events(limit))


@app.route("/api/strategies", methods=["GET", "POST"])
def strategies_endpoint() -> Response:
    """전략 설정을 조회하거나 업데이트"""
    if request.method == "GET":
        src = request.args.get("source", "latest")
        if src == "yesterday":
            settings = load_strategy_settings(STRATEGY_YDAY_FILE)
        elif src == "default":
            settings = load_strategy_settings(None)
        else:
            settings = load_strategy_settings(STRATEGY_SETTINGS_FILE)
        master = {s["short_code"]: s for s in load_strategy_master()}
        data = []
        for s in settings:
            m = master.get(s["short_code"], {})
            data.append({
                "name": s["short_code"],
                "info": m.get("buy_formula", ""),
                "on": s.get("on", True),
                "order": s.get("order", 1),
                "rc": 0, "rw": "0%", "rr": "0%",
                "pc": 0, "pw": "0%", "pr": "0%",
                "data": "기본값",
            })
        ts = ""
        if os.path.exists(STRATEGY_SETTINGS_FILE):
            ts = datetime.datetime.fromtimestamp(os.path.getmtime(STRATEGY_SETTINGS_FILE)).strftime("%Y-%m-%d %H:%M:%S")
        return jsonify({"strategies": data, "updated_at": ts})

    payload = request.get_json(force=True) or []
    if isinstance(payload, dict) and "strategies" in payload:
        payload = payload["strategies"]
    settings = [
        {"short_code": s.get("short_code") or s.get("name"),
         "on": bool(s.get("on", True)),
         "order": int(s.get("order", 1))}
        for s in payload
    ]
    if os.path.exists(STRATEGY_SETTINGS_FILE):
        try:
            prev = load_strategy_settings(STRATEGY_SETTINGS_FILE)
            save_strategy_settings(prev, STRATEGY_YDAY_FILE)
        except Exception:
            pass
    save_strategy_settings(settings, STRATEGY_SETTINGS_FILE)
    reload_strategy_settings()
    ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return jsonify({"status": "ok", "updated_at": ts})


@app.route("/api/risk_events")
def risk_events_endpoint() -> Response:
    """SQLite 로그에서 최근 리스크 매니저 이벤트 조회"""
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
    """현재 거래 유니버스를 보여주는 첫 페이지"""
    universe = get_universe()
    if not universe:
        universe = select_universe(CONFIG)
    return render_template("index.html", universe=universe)


@app.route("/dashboard")
def dashboard():
    """대시보드 메인 페이지 렌더링"""
    universe = get_universe()
    if not universe:
        universe = select_universe(CONFIG)
    return render_template("01_Home.html", universe=universe, config=CONFIG)


@app.route("/strategy")
def strategy():
    """전략 설정 페이지 렌더링"""
    return render_template("02_Strategy.html")


@app.route("/risk")
def risk():
    """리스크 관리 페이지 렌더링"""
    return render_template("03_Risk.html")


@app.route("/analysis")
def analysis():
    """데이터 분석 페이지 렌더링"""
    return render_template("04_Analysis.html")


@app.route("/settings")
def settings():
    """개인 설정 페이지 렌더링"""
    return render_template("05_pSettings.html")
# 시작 시 자동 매매를 강제로 끄고 모니터링 루프 시작
save_auto_trade_status({
    "enabled": False,
    "updated_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
})
start_monitoring()


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [F1-F2] [%(levelname)s] %(message)s",
        handlers=[
            RotatingFileHandler(
                "logs/F1-F2_loop.log",
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
    app.run(host="0.0.0.0", port=PORT, debug=True)
