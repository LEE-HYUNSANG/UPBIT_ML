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
from pathlib import Path
from signal_loop import process_symbol, main_loop
import threading
from common_utils import ensure_utf8_stdout, save_json
from f6_setting.buy_config import load_buy_config, save_buy_config
from f6_setting import alarm_control
from f1_universe.universe_selector import (
    select_universe,
    load_config,
    get_universe,
    schedule_universe_updates,
    update_universe,
    load_universe_from_file,
    CONFIG_PATH,
)
from importlib import import_module
import importlib.util

_se = import_module("f2_ml_buy_signal.03_buy_signal_engine.signal_engine")
reload_strategy_settings = _se.reload_strategy_settings

app = Flask(__name__)
PORT = int(os.environ.get("PORT", 3000))

CONFIG = load_config()
load_universe_from_file()
schedule_universe_updates(1800, CONFIG)

CFG_DIR = "config"
LATEST_CFG = os.path.join(CFG_DIR, "f6_buy_settings.json")
DEFAULT_CFG = LATEST_CFG
ML_CFG = LATEST_CFG
YDAY_CFG = LATEST_CFG

RISK_CONFIG_PATH = LATEST_CFG

AUTOTRADE_STATUS_FILE = os.path.join("config", "web_autotrade_status.json")
EVENTS_LOG = os.path.join("logs", "etc", "events.jsonl")

STRATEGY_SETTINGS_FILE = os.path.join("config", "app_f2_strategy_settings.json")
STRATEGY_YDAY_FILE = os.path.join("config", "strategy_settings_yesterday.json")
STRATEGIES_MASTER_FILE = "strategies_master_pruned.json"
BUY_SETTINGS_FILE = os.path.join("config", "f6_buy_settings.json")
ALARM_CONFIG_FILE = alarm_control.CONFIG_FILE

BUY_LIST_FILE = os.path.join("config", "f2_f2_realtime_buy_list.json")
SELL_LIST_FILE = os.path.join("config", "f3_f3_realtime_sell_list.json")
MONITORING_LIST_FILE = os.path.join("config", "f5_f1_monitoring_list.json")

# 자동 매매 스레드의 실행 상태 보관용 변수
_auto_trade_thread = None
_auto_trade_stop = None
_monitor_thread = None
_monitor_stop = None
_data_collect_thread = None
_buy_signal_thread = None
_pipeline_thread = None
_refresh_thread = None
_buy_signal_stop = None
_pipeline_stop = None
_refresh_stop = None


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


def load_buy_settings() -> dict:
    return load_buy_config(BUY_SETTINGS_FILE)


def save_buy_settings(data: dict) -> None:
    save_buy_config(data, BUY_SETTINGS_FILE)


def load_alarm_settings() -> dict:
    return alarm_control.load_config(ALARM_CONFIG_FILE)


def save_alarm_settings(data: dict) -> None:
    alarm_control.save_config(data, ALARM_CONFIG_FILE)


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


def reset_state_files() -> None:
    """Initialize runtime JSON files on app startup."""
    save_json(BUY_LIST_FILE, [])
    save_json(SELL_LIST_FILE, [])
    save_json(MONITORING_LIST_FILE, [])


def init_sell_list_from_positions() -> None:
    """Record currently held symbols into the realtime sell list."""
    from f3_order.order_executor import _default_executor

    symbols = [
        p.get("symbol")
        for p in _default_executor.position_manager.positions
        if p.get("status") == "open"
    ]
    save_json(SELL_LIST_FILE, symbols)

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
    try:
        from f6_setting.remote_control import write_status
        write_status("ON")
    except Exception:
        pass


def stop_auto_trade() -> None:
    """실행 중인 자동 매매 루프 중지"""
    global _auto_trade_thread, _auto_trade_stop
    if _auto_trade_stop:
        _auto_trade_stop.set()
    _auto_trade_thread = None
    start_monitoring()
    try:
        from f6_setting.remote_control import write_status
        write_status("OFF")
    except Exception:
        pass


def start_monitoring() -> None:
    """신규 진입 없이 위험 모니터링 루프 실행"""
    global _monitor_thread, _monitor_stop
    if _monitor_thread and _monitor_thread.is_alive():
        return
    from signal_loop import RiskManager, _default_executor  # lazy import
    _monitor_stop = threading.Event()

    def monitor_worker():
        if callable(RiskManager):
            rm = RiskManager(
                order_executor=_default_executor,
                exception_handler=_default_executor.exception_handler,
            )
            if hasattr(rm, "config"):
                rm.config._cache.update(load_buy_settings())
            _default_executor.set_risk_manager(rm)
        else:
            rm = None
        while not _monitor_stop.is_set():
            open_syms = [
                p.get("symbol")
                for p in _default_executor.position_manager.positions
                if p.get("status") == "open"
            ]
            if rm:
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


def _import_from_path(path: str, name: str):
    """Import module from ``path`` under ``name`` preserving singletons."""
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    sys.modules[name] = module
    return module


def start_data_collection() -> None:
    """Start the continuous data collector in a background thread."""
    global _data_collect_thread
    if _data_collect_thread and _data_collect_thread.is_alive():
        return
    module = _import_from_path(os.path.join("f5_ml_pipeline", "01_data_collect.py"), "f5_data_collect")
    _data_collect_thread = threading.Thread(target=module.main, daemon=True)
    _data_collect_thread.start()


def start_buy_signal_scheduler() -> None:
    """Run the ML buy signal script every 15 seconds."""
    global _buy_signal_thread, _buy_signal_stop
    if _buy_signal_thread and _buy_signal_thread.is_alive():
        return
    module = _import_from_path(os.path.join("f2_ml_buy_signal", "02_ml_buy_signal.py"), "f2_ml_buy")
    buy_exec = _import_from_path(
        os.path.join("f2_ml_buy_signal", "03_buy_signal_engine", "buy_list_executor.py"),
        "buy_list_executor",
    )
    _buy_signal_stop = threading.Event()

    def worker():
        while not _buy_signal_stop.is_set():
            try:
                module.run_if_monitoring_list_exists()
                buy_exec.execute_buy_list()
            except Exception:
                WEB_LOGGER.exception("buy signal error")
            if _buy_signal_stop.wait(15):
                break

    _buy_signal_thread = threading.Thread(target=worker, daemon=True)
    _buy_signal_thread.start()


def stop_buy_signal_scheduler() -> None:
    global _buy_signal_thread, _buy_signal_stop
    if _buy_signal_stop:
        _buy_signal_stop.set()
    _buy_signal_thread = None


def start_pipeline_scheduler() -> None:
    """Run the full ML pipeline every five minutes."""
    global _pipeline_thread, _pipeline_stop
    if app.debug and os.environ.get("WERKZEUG_RUN_MAIN") != "true":
        return
    if _pipeline_thread and _pipeline_thread.is_alive():
        return
    module = _import_from_path(os.path.join("f5_ml_pipeline", "run_pipeline.py"), "run_pipeline")
    _pipeline_stop = threading.Event()

    def worker():
        while not _pipeline_stop.is_set():
            try:
                module.main()
            except Exception:
                WEB_LOGGER.exception("pipeline error")
            if _pipeline_stop.wait(300):
                break

    _pipeline_thread = threading.Thread(target=worker, daemon=True)
    _pipeline_thread.start()


def stop_pipeline_scheduler() -> None:
    global _pipeline_thread, _pipeline_stop
    if _pipeline_stop:
        _pipeline_stop.set()
    _pipeline_thread = None


def start_full_refresh_scheduler() -> None:
    """Run ``00_72h_1min_data.py`` every 20 minutes."""
    global _refresh_thread, _refresh_stop
    if app.debug and os.environ.get("WERKZEUG_RUN_MAIN") != "true":
        return
    if _refresh_thread and _refresh_thread.is_alive():
        return
    module = _import_from_path(os.path.join("f5_ml_pipeline", "00_72h_1min_data.py"), "f5_72h")
    _refresh_stop = threading.Event()

    def worker():
        while not _refresh_stop.is_set():
            try:
                module.main()
            except Exception as exc:
                WEB_LOGGER.error("72h refresh error: %s", exc)
            if _refresh_stop.wait(1200):
                break

    _refresh_thread = threading.Thread(target=worker, daemon=True)
    _refresh_thread.start()


def stop_full_refresh_scheduler() -> None:
    global _refresh_thread, _refresh_stop
    if _refresh_stop:
        _refresh_stop.set()
    _refresh_thread = None


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
    os.makedirs("logs/etc", exist_ok=True)
    handler = RotatingFileHandler(
        "logs/etc/web.log",
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


@app.route("/api/buy_monitoring")
def api_buy_monitoring() -> Response:
    """Return buy monitoring list with F2 metrics."""
    buy_path = os.path.join("config", "f2_f2_realtime_buy_list.json")
    try:
        with open(buy_path, "r", encoding="utf-8") as f:
            buy_list = json.load(f)
        if not isinstance(buy_list, list):
            buy_list = []
    except Exception:  # pragma: no cover - missing file
        buy_list = []

    metrics_path = os.path.join(
        "f5_ml_pipeline", "ml_data", "10_selected", "selected_strategies.json"
    )
    metrics = {}
    try:
        with open(metrics_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):
            for rec in data:
                sym = rec.get("symbol")
                if sym:
                    metrics[sym] = {
                        "win_rate": float(rec.get("win_rate", 0.0)),
                        "avg_roi": float(rec.get("avg_roi", 0.0)),
                    }
    except Exception:  # pragma: no cover - optional file
        metrics = {}

    version = ""
    try:
        mtime = os.path.getmtime(metrics_path)
        version = datetime.datetime.fromtimestamp(mtime).strftime("%m%d_%H%M")
    except Exception:  # pragma: no cover - missing file
        version = ""

    rows = []
    for item in buy_list:
        if not isinstance(item, dict):
            continue
        sym = item.get("symbol")
        m = metrics.get(sym, {})
        rows.append(
            {
                "symbol": sym,
                "ml_signal": item.get("buy_signal"),
                "trend_sel": item.get("trend_sel"),
                "rsi_sel": item.get("rsi_sel"),
                "version": version,
                "win_rate": m.get("win_rate"),
                "avg_roi": m.get("avg_roi"),
            }
        )

    return jsonify(rows)


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


@app.route("/api/buy_settings", methods=["GET", "POST"])
def buy_settings_endpoint() -> Response:
    """매수 설정 조회 또는 업데이트"""
    if request.method == "GET":
        return jsonify(load_buy_settings())
    data = request.get_json(force=True) or {}
    save_buy_settings(data)
    return jsonify({"status": "ok"})


@app.route("/api/alarm_config", methods=["GET", "POST"])
def alarm_config_endpoint() -> Response:
    """텔레그램 알림 설정 조회 또는 업데이트"""
    if request.method == "GET":
        return jsonify(load_alarm_settings())
    data = request.get_json(force=True) or {}
    save_alarm_settings(data)
    return jsonify({"status": "ok"})



@app.route("/")
def home():
    """Dashboard landing page"""
    universe = get_universe()
    if not universe:
        universe = select_universe(CONFIG)
    return render_template("dashboard.html", universe=universe, config=CONFIG)


@app.route("/dashboard")
def dashboard():
    """Dashboard page"""
    universe = get_universe()
    if not universe:
        universe = select_universe(CONFIG)
    return render_template("dashboard.html", universe=universe, config=CONFIG)




@app.route("/settings")
def settings():
    """Notification settings page"""
    return render_template("settings.html")
# 시작 시 자동 매매를 강제로 끄고 모니터링 루프 시작
save_auto_trade_status({
    "enabled": False,
    "updated_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
})
reset_state_files()
start_monitoring()
init_sell_list_from_positions()


if __name__ == "__main__":
    ensure_utf8_stdout()
    Path("logs/etc").mkdir(parents=True, exist_ok=True)
    Path("logs/f1").mkdir(parents=True, exist_ok=True)
    Path("logs/f2").mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [F1-F2] [%(levelname)s] %(message)s",
        handlers=[
            RotatingFileHandler(
                Path("logs/etc/F1-F2_loop.log"),
                encoding="utf-8",
                maxBytes=100_000 * 1024,
                backupCount=1000,
            ),
            RotatingFileHandler(
                Path("logs/f1/F1_signal_engine.log"),
                encoding="utf-8",
                maxBytes=100_000 * 1024,
                backupCount=1000,
            ),
            RotatingFileHandler(
                Path("logs/f2/F2_signal_engine.log"),
                encoding="utf-8",
                maxBytes=100_000 * 1024,
                backupCount=1000,
            ),
            logging.StreamHandler(),
        ],
        force=True,
    )
    if not app.debug or os.environ.get("WERKZEUG_RUN_MAIN") == "true":
        start_data_collection()
        start_buy_signal_scheduler()
        start_pipeline_scheduler()
        start_full_refresh_scheduler()

    app.run(host="0.0.0.0", port=PORT, debug=True)
