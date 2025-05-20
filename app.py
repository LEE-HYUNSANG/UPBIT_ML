"""
UPBIT 5분봉 자동매매 Flask 메인 앱 (초보자 상세 주석)
"""
from flask import Flask, render_template, jsonify, request, send_file
from flask_socketio import SocketIO
import os
import shutil
import logging
import json  # 기본 모듈들
from datetime import datetime

from utils import load_secrets, send_telegram, setup_logging
from bot.trader import UpbitTrader
from bot.runtime_settings import settings, load_from_file
import pyupbit
import threading
import time

app = Flask(__name__)  # Flask 애플리케이션 생성
socketio = SocketIO(app, cors_allowed_origins="*")  # 실시간 알림용 SocketIO

# 로그 설정 (파일 + 콘솔)
logger = setup_logging()

# 숫자 천 단위 콤마 필터
@app.template_filter('comma')
def comma_format(value):
    try:
        return f"{int(value):,}"
    except (ValueError, TypeError):
        return value


@app.before_request
def log_request():
    logger.debug(
        "HTTP REQUEST %s %s args=%s json=%s",
        request.method,
        request.path,
        dict(request.args),
        request.get_json(silent=True),
    )


@app.after_request
def log_response(response):
    logger.debug(
        "HTTP RESPONSE %s %s status=%s",
        request.method,
        request.path,
        response.status,
    )
    return response

# 샘플 설정 로드
with open("config/config.json", encoding="utf-8") as f:
    config = json.load(f)

# config 파일 값을 전역 settings 에 반영
load_from_file()

# secrets.json 을 공통 로더로 읽기
secrets = load_secrets()

# 기본 계좌 요약 자리표시자
ACCOUNT_PLACEHOLDER = {
    "cash": "현재 로딩중...",
    "total": "현재 로딩중...",
    "pnl": "현재 로딩중...",
}

# 캐시 형태로 계좌 요약을 저장 (초기값은 로딩중)
account_cache = ACCOUNT_PLACEHOLDER.copy()

# RuntimeSettings dataclass 로 설정 관리


# 대시보드 코인 필터 설정 로드/저장용
FILTER_FILE = 'config/filter.json'
filter_config = {"min_price": 0, "max_price": 0, "rank": 0}
if os.path.exists(FILTER_FILE):
    try:
        with open(FILTER_FILE, encoding='utf-8') as f:
            filter_config.update(json.load(f))
    except Exception:
        pass

# 매도 모니터링 제외 목록 로드
EXCLUDE_FILE = 'config/exclude.json'
excluded_coins = []
if os.path.exists(EXCLUDE_FILE):
    try:
        with open(EXCLUDE_FILE, encoding='utf-8') as f:
            excluded_coins = json.load(f)
    except Exception:
        excluded_coins = []



# 트레이더 인스턴스 (실제 매매 로직)
trader = UpbitTrader(
    secrets.get("UPBIT_KEY", ""),
    secrets.get("UPBIT_SECRET", ""),
    config,
    logger=logger,
)

def notify_error(message: str, code: str) -> None:
    """Log, socket emit and send Telegram alert for an error with a code."""
    full = f"[{code}] {message}"
    logger.error(full)
    socketio.emit('notification', {'message': full})
    token = secrets.get('TELEGRAM_TOKEN')
    chat_id = secrets.get('TELEGRAM_CHAT_ID')
    if token and chat_id:
        send_telegram(token, chat_id, full)

def get_balances():
    """Fetch current coin balances from trader."""
    logger.debug("Fetching balances")
    data = trader.get_balances()
    if data is None:
        return []
    if excluded_coins:
        ex_ids = {c['coin'] for c in excluded_coins}
        data = [b for b in data if b.get('currency') not in ex_ids]
    return data


def get_status() -> dict:
    """Return current running status and last update time."""
    logger.debug("Fetching status")
    return {"running": settings.running, "updated": settings.updated}


def get_account_summary():
    logger.debug("Fetching account summary")
    global account_cache
    excluded = {c['coin'] for c in excluded_coins} if excluded_coins else None
    summary = trader.account_summary(excluded)
    if summary is None:
        account_cache = {
            "cash": "네트워크 연결 안됨",
            "total": "네트워크 연결 안됨",
            "pnl": "네트워크 연결 안됨",
        }
    else:
        account_cache = summary
    return account_cache

def update_timestamp() -> None:
    """Update last change timestamp in settings."""
    settings.update_timestamp()

def save_excluded():
    os.makedirs(os.path.dirname(EXCLUDE_FILE), exist_ok=True)
    with open(EXCLUDE_FILE, 'w', encoding='utf-8') as f:
        json.dump(excluded_coins, f, ensure_ascii=False, indent=2)

positions = []

# Market data and monitoring file paths
MARKET_FILE = "config/market.json"
MONITOR_FILE = "config/monitor_list.json"

# 실시간 시세/거래량 캐시
_market_lock = threading.Lock()
market_cache: list[dict] = []


def save_market_file(data: list[dict]) -> None:
    """Save fetched market data to ``MARKET_FILE``."""
    os.makedirs(os.path.dirname(MARKET_FILE), exist_ok=True)
    with open(MARKET_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def update_monitor_list() -> None:
    """Apply dashboard filter to market data and save results."""
    signals = get_filtered_signals()
    os.makedirs(os.path.dirname(MONITOR_FILE), exist_ok=True)
    with open(MONITOR_FILE, "w", encoding="utf-8") as f:
        json.dump(signals, f, ensure_ascii=False, indent=2)
    logger.debug("[MARKET] Monitor list saved %d coins", len(signals))


def refresh_market_data() -> None:
    """Fetch KRW coin prices and volumes from Upbit."""
    global market_cache
    try:
        tickers = pyupbit.get_tickers(fiat="KRW")
        prices = pyupbit.get_current_price(tickers) or {}
        data = []
        for t in tickers:
            # use 1-hour volume for ranking
            df = pyupbit.get_ohlcv(t, interval="minute60", count=1)
            vol = 0
            if df is not None and not df.empty:
                vol = float(df["volume"].iloc[-1])
            price = prices.get(t) if isinstance(prices, dict) else prices
            if price is None:
                price = 0
            logger.debug("[MARKET] fetched %s price=%.8f vol=%.2f", t, price, vol)
            data.append({"coin": t.split("-")[-1], "price": float(price), "volume": vol})
        data.sort(key=lambda x: x["volume"], reverse=True)
        for i, d in enumerate(data, start=1):
            d["rank"] = i
            d.update({
                "trend": "",
                "volatility": "",
                "strength": "",
                "gc": "",
                "rsi": "",
                "signal": "관망",
                "signal_class": "wait",
                "key": "MBREAK",
            })
            logger.debug(
                "[MARKET] ranked %s price=%.8f vol=%.2f rank=%d",
                d["coin"],
                d["price"],
                d["volume"],
                i,
            )            
        with _market_lock:
            market_cache = data
        logger.debug("[MARKET] Updated %d coins", len(data))
        save_market_file(data)
        update_monitor_list()
    except Exception as e:
        logger.exception("Market data fetch failed: %s", e)


def market_refresh_loop() -> None:
    """Background updater for market_cache."""
    while True:
        refresh_market_data()
        time.sleep(60)


def buy_signal_monitor_loop() -> None:
    """Monitor filtered coins every 10 seconds for buy signals."""
    while True:
        try:
            with open(MONITOR_FILE, "r", encoding="utf-8") as f:
                coins = json.load(f)
        except Exception:
            coins = []
        logger.debug("[BUY MONITOR] checking %d coins", len(coins))
        # Placeholder for real signal generation
        time.sleep(10)

def get_filtered_signals():
    """Return market data filtered by price range and volume rank."""
    logger.info("[MONITOR] 매수 모니터링 요청")
    logger.debug("[MONITOR] 필터 조건 %s", filter_config)
    min_p = float(filter_config.get("min_price", 0) or 0)
    max_p = float(filter_config.get("max_price", 0) or 0)
    rank = int(filter_config.get("rank", 0) or 0)
    with _market_lock:
        data = list(market_cache)

    filtered = []
    for s in data:
        logger.debug("[MONITOR] 원본 시그널 %s", s)
        price = s["price"]
        if min_p and price < min_p:
            logger.debug(
                "[MONITOR] 제외 %s price %.8f < min_price %.8f",
                s["coin"],
                price,
                min_p,
            )
            continue
        if max_p and max_p > 0 and price > max_p:
            logger.debug(
                "[MONITOR] 제외 %s price %.8f > max_price %.8f",
                s["coin"],
                price,
                max_p,
            )
            continue
        filtered.append(s)

    if rank:
        filtered = filtered[:rank]

    result = []
    for s in filtered:
        entry = {k: v for k, v in s.items() if k != "rank"}
        logger.debug(
            "[MONITOR] 선정 %s price %.8f rank %d",
            entry["coin"],
            s["price"],
            s["rank"],
        )
        result.append(entry)

    logger.info("[MONITOR] UPBIT 응답 %d개", len(result))
    for s in result:
        logger.debug("[MONITOR] 응답 데이터 %s", s)
    return result

def get_filtered_tickers() -> list[str]:
    """Return KRW tickers filtered by dashboard conditions."""
    logger.debug("Filtering tickers with %s", filter_config)
    signals = get_filtered_signals()
    tickers = [f"KRW-{s['coin']}" for s in signals]
    logger.debug("Filtered tickers: %s", tickers)
    return tickers


# Initial data load and background threads
refresh_market_data()
threading.Thread(target=market_refresh_loop, daemon=True).start()
threading.Thread(target=buy_signal_monitor_loop, daemon=True).start()

alerts = []
history = [
    {"time": "2025-05-18 13:00", "label": "적용", "cls": "success"},
    {"time": "2025-05-17 10:13", "label": "분석", "cls": "primary"},
]
    
buy_results = []
sell_results = []

# 기본 전략 정보 (9전략 모두 표시)
strategies = [
    {
        "name": s["name"],
        "key": s["key"],
        "enabled": i == 0,
        "tp": 0.02,
        "sl": 0.01,
        "trail": 0.012,
        "option": s["buy"]["cond"][0] if s.get("buy", {}).get("cond") else "",
        "recommend": "TP2% SL1%",
        "desc": " / ".join(s["buy"]["cond"][:2]) if s.get("buy", {}).get("cond") else "",
    }
    for i, s in enumerate(
        [
            {
                "key": "MBREAK",
                "name": "M-BREAK",
                "buy": {"cond": ["강한 추세 돌파"]},
            },
            {"key": "PPULL", "name": "P-PULL", "buy": {"cond": ["조정 매수"]}},
            {"key": "TFLOW", "name": "T-FLOW", "buy": {"cond": ["추세/OBV"]}},
            {"key": "BLOW", "name": "B-LOW", "buy": {"cond": ["박스권 하단"]}},
            {"key": "VREV", "name": "V-REV", "buy": {"cond": ["대폭락 반등"]}},
            {"key": "GREV", "name": "G-REV", "buy": {"cond": ["골든크로스"]}},
            {"key": "VOLBRK", "name": "VOL-BRK", "buy": {"cond": ["ATR 폭발"]}},
            {"key": "EMASTACK", "name": "EMA-STACK", "buy": {"cond": ["다중정렬"]}},
            {"key": "VWAPBNC", "name": "VWAP-BNC", "buy": {"cond": ["VWAP 근접"]}},
        ]
    )
]

# AI 분석 페이지에서 사용될 상세 전략 정보
analysis_strategies = [
    {
        "key": "MBREAK",
        "name": "M-BREAK",
        "buy": {
            "cond": [
                "5EMA > 20EMA > 60EMA",
                "ATR ≥ 0.035",
                "20봉 평균 거래량의 1.8배 이상",
                "전고점 0.15% 돌파 시 진입"
            ],
            "ai": [
                "RSI < 26",
                "TP(익절) 1.8%",
                "SL(손절) 1.0%",
                "분할 진입: 단일"
            ]
        },
        "sell": {
            "cond": [
                "손절: -1.1%",
                "트레일링 익절: 1.4%"
            ],
            "ai": [
                "SL(손절) 1.1%",
                "트레일링 1.4%"
            ]
        }
    },
    {
        "key": "PPULL",
        "name": "P-PULL",
        "buy": {
            "cond": [
                "5EMA > 20EMA > 60EMA",
                "RSI ≤ 24",
                "50EMA 근접",
                "직전 봉 대비 거래량 1.2배↑"
            ],
            "ai": [
                "TP(익절) 2.2%",
                "SL(손절) 1.1%",
                "분할 매수: 3회"
            ]
        },
        "sell": {
            "cond": [
                "손절: -1.2%",
                "트레일링 익절: 1.5%"
            ],
            "ai": [
                "SL(손절) 1.2%",
                "트레일링 1.5%"
            ]
        }
    },
    {
        "key": "TFLOW",
        "name": "T-FLOW",
        "buy": {
            "cond": [
                "EMA20 5봉 기울기 > 0.15%",
                "OBV 3봉 연속 상승",
                "RSI 48~60"
            ],
            "ai": [
                "TP(익절) 3.0%"
            ]
        },
        "sell": {
            "cond": [
                "손절: -1.3%",
                "트레일링 익절: 1.7%"
            ],
            "ai": [
                "SL(손절) 1.3%",
                "트레일링 1.7%"
            ]
        }
    },
    {
        "key": "BLOW",
        "name": "B-LOW",
        "buy": {
            "cond": [
                "박스권 하단, 박스폭 6% 이내",
                "저점 터치, RSI 25 미만 반등"
            ],
            "ai": [
                "TP(익절) 2.5%",
                "SL(손절) 1.3%",
                "RSI < 22"
            ]
        },
        "sell": {
            "cond": [
                "손절: -1.3%",
                "트레일링 익절: 1.1%"
            ],
            "ai": [
                "SL(손절) 1.3%",
                "트레일링 1.1%"
            ]
        }
    },
    {
        "key": "VREV",
        "name": "V-REV",
        "buy": {
            "cond": [
                "전봉 종가 -4%↓",
                "거래량 2.5배↑",
                "RSI 18→상승"
            ],
            "ai": [
                "TP(익절) 1.7%"
            ]
        },
        "sell": {
            "cond": [
                "손절: -1.2%",
                "트레일링 익절: 1.5%"
            ],
            "ai": [
                "SL(손절) 1.2%",
                "트레일링 1.5%"
            ]
        }
    },
    {
        "key": "GREV",
        "name": "G-REV",
        "buy": {
            "cond": [
                "EMA50 > 200 골든크로스",
                "단기 눌림, RSI 48 이상"
            ],
            "ai": [
                "TP(익절) 1.5%"
            ]
        },
        "sell": {
            "cond": [
                "손절: -1.2%",
                "트레일링 익절: 1.4%"
            ],
            "ai": [
                "SL(손절) 1.2%",
                "트레일링 1.4%"
            ]
        }
    },
    {
        "key": "VOLBRK",
        "name": "VOL-BRK",
        "buy": {
            "cond": [
                "ATR폭발(10봉대비 1.5배↑)",
                "20봉 거래량 2배↑",
                "RSI≥60"
            ],
            "ai": [
                "TP(익절) 1.9%"
            ]
        },
        "sell": {
            "cond": [
                "손절: -1.1%",
                "트레일링 익절: 1.5%"
            ],
            "ai": [
                "SL(손절) 1.1%",
                "트레일링 1.5%"
            ]
        }
    },
    {
        "key": "EMASTACK",
        "name": "EMA-STACK",
        "buy": {
            "cond": [
                "EMA25>100>200",
                "ADX > 30"
            ],
            "ai": [
                "TP(익절) 1.5%"
            ]
        },
        "sell": {
            "cond": [
                "손절: -1.3%",
                "트레일링 익절: 1.2%"
            ],
            "ai": [
                "SL(손절) 1.3%",
                "트레일링 1.2%"
            ]
        }
    },
    {
        "key": "VWAPBNC",
        "name": "VWAP-BNC",
        "buy": {
            "cond": [
                "EMA5>20>60, 종가 VWAP 근접",
                "RSI 45~60",
                "거래량 증가"
            ],
            "ai": [
                "TP(익절) 1.7%"
            ]
        },
        "sell": {
            "cond": [
                "손절: -1.1%",
                "트레일링 익절: 1.3%"
            ],
            "ai": [
                "SL(손절) 1.1%",
                "트레일링 1.3%"
            ]
        }
    }
]

@app.route("/")
def dashboard():
    logger.debug("Render dashboard")
    data = get_balances()
    ex_ids = {c['coin'] for c in excluded_coins} if excluded_coins else None
    current_positions = trader.build_positions(data, ex_ids) if data else []
    return render_template(
        "index.html",
        running=settings.running,
        positions=current_positions,
        alerts=alerts,
        signals=get_filtered_signals(),
        updated=settings.updated,
        account=get_account_summary(),
        config=filter_config,
    )

@app.route("/strategy")
def strategy_page():
    logger.debug("Render strategy page")
    return render_template("strategy.html", strategies=strategies, settings=settings)

# AI 전략 분석 페이지
@app.route("/ai-analysis")
def ai_analysis_page():
    logger.debug("Render AI analysis page")
    return render_template(
        "ai_analysis.html",
        buy_results=buy_results,
        sell_results=sell_results,
        history=history,
        strategies=analysis_strategies,
    )

@app.route("/risk")
def risk_page():
    logger.debug("Render risk page")
    risk = {
        "daily": 2, "weekly": 5, "monthly": 10,
        "push": True, "telegram": True,
        "force_pct": 5, "force_count": 3,
        "cont_loss": 4, "cont_profit": 5,
        "log_path": "logs/trades.csv", "updated": settings.updated
    }
    return render_template("risk.html", risk=risk)

@app.route("/notifications")
def notifications_page():
    logger.debug("Render notifications page")
    return render_template(
        "notifications.html",
        alerts=alerts,
        alert_config=config.get("alerts", {})
    )

@app.route("/funds")
def funds_page():
    logger.debug("Render funds page")
    return render_template("funds.html", settings=settings)

@app.route("/settings")
def settings_page():
    logger.debug("Render settings page")
    return render_template("settings.html", settings=settings, secrets=secrets)

@app.route("/api/start-bot", methods=["POST"])
def start_bot():
    logger.debug("start_bot called")
    logger.info("[API] 봇 시작 요청")
    try:
        trader.set_tickers(get_filtered_tickers())
        started = trader.start()
        if not started:
            logger.info("Start request ignored: already running")
            return jsonify(result="error", message="봇이 이미 실행중입니다.", status=get_status())
        settings.running = True
        socketio.emit('notification', {'message': '봇이 시작되었습니다.'})
        token = secrets.get("TELEGRAM_TOKEN")
        chat_id = secrets.get("TELEGRAM_CHAT_ID")
        if config.get("alerts", {}).get("telegram") and token and chat_id:
            send_telegram(token, chat_id, "봇이 시작되었습니다.")
        update_timestamp()
        logger.info("Bot started")
        return jsonify(result="success", message="봇이 시작되었습니다.", status=get_status())
    except Exception as e:
        notify_error(f"봇 시작 실패: {e}", "E001")
        return jsonify(result="error", message="봇 시작 실패"), 500

@app.route("/api/stop-bot", methods=["POST"])
def stop_bot():
    logger.debug("stop_bot called")
    logger.info("[API] 봇 중지 요청")
    try:
        stopped = trader.stop()
        if not stopped:
            logger.info("Stop request ignored: not running")
            return jsonify(result="error", message="봇이 이미 중지되어 있습니다.", status=get_status())
        settings.running = False
        socketio.emit('notification', {'message': '봇이 정지되었습니다.'})
        token = secrets.get("TELEGRAM_TOKEN")
        chat_id = secrets.get("TELEGRAM_CHAT_ID")
        if config.get("alerts", {}).get("telegram") and token and chat_id:
            send_telegram(token, chat_id, "봇이 정지되었습니다.")
        update_timestamp()
        return jsonify(result="success", message="봇이 정지되었습니다.", status=get_status())
    except Exception as e:
        notify_error(f"봇 중지 실패: {e}", "E002")
        return jsonify(result="error", message="봇 중지 실패"), 500

@app.route("/api/apply-strategy", methods=["POST"])
def apply_strategy():
    data = request.json
    logger.debug("apply_strategy called with %s", data)
    logger.info(f"[API] 전략 적용: {data}")
    try:
        settings.strategy = data.get("strategy", settings.strategy)
        socketio.emit('notification', {'message': '전략이 적용되었습니다.'})
        logger.info("Strategy applied")
        return jsonify(result="success", message="전략이 적용되었습니다.")
    except Exception as e:
        notify_error(f"전략 적용 실패: {e}", "E003")
        return jsonify(result="error", message="전략 적용 실패"), 500

@app.route("/api/save-settings", methods=["POST"])
def save_settings():
    data = request.get_json(silent=True) or {}
    logger.debug("save_settings called with %s", data)
    try:
        if not isinstance(data, dict):
            raise ValueError("Invalid JSON")
        # 대시보드 필터 값 저장
        for k in ("min_price", "max_price", "rank"):
            if k in data:
                value = data[k]
                if value in (None, ""):
                    continue
                try:
                    if k == "rank":
                        filter_config[k] = int(value)
                    else:
                        filter_config[k] = float(value)
                except (ValueError, TypeError):
                    raise ValueError(f"Invalid value for {k}")
        for k, v in data.items():
            if k in ("min_price", "max_price", "rank"):
                continue
            if hasattr(settings, k):
                setattr(settings, k, v)
        os.makedirs(os.path.dirname(FILTER_FILE), exist_ok=True)
        with open(FILTER_FILE, "w", encoding="utf-8") as f:
            json.dump(filter_config, f, ensure_ascii=False, indent=2)
        update_timestamp()
        socketio.emit('notification', {'message': '설정이 저장되었습니다.'})
        logger.info("Settings saved: %s", json.dumps(data, ensure_ascii=False))
        return jsonify(result="success", message="저장 완료", status=get_status())
    except Exception as e:
        notify_error(f"설정 저장 실패: {e}", "E004")
        if isinstance(e, ValueError):
            return jsonify(result="error", message=str(e)), 400
        return jsonify(result="error", message="설정 저장 실패"), 500

@app.route("/api/save-risk", methods=["POST"])
def save_risk():
    data = request.json
    logger.debug("save_risk called with %s", data)
    try:
        socketio.emit('notification', {'message': '리스크 설정 저장'})
        logger.info("Risk settings saved: %s", json.dumps(data, ensure_ascii=False))
        return jsonify(result="success", message="리스크 저장 완료")
    except Exception as e:
        notify_error(f"리스크 저장 실패: {e}", "E005")
        return jsonify(result="error", message="리스크 저장 실패"), 500

@app.route("/api/save-alerts", methods=["POST"])
def save_alerts():
    data = request.json
    logger.debug("save_alerts called with %s", data)
    try:
        socketio.emit('notification', {'message': '알림 설정 저장'})
        logger.info("Alert settings saved: %s", json.dumps(data, ensure_ascii=False))
        return jsonify(result="success", message="알림 설정 저장 완료")
    except Exception as e:
        notify_error(f"알림 설정 저장 실패: {e}", "E006")
        return jsonify(result="error", message="알림 저장 실패"), 500

@app.route("/api/save-funds", methods=["POST"])
def save_funds():
    data = request.json
    logger.debug("save_funds called with %s", data)
    try:
        for k, v in data.items():
            if hasattr(settings, k):
                setattr(settings, k, v)
        socketio.emit('notification', {'message': '자금 설정 저장'})
        logger.info("Funds settings saved: %s", json.dumps(data, ensure_ascii=False))
        return jsonify(result="success", message="자금 설정 저장 완료")
    except Exception as e:
        notify_error(f"자금 설정 저장 실패: {e}", "E007")
        return jsonify(result="error", message="자금 저장 실패"), 500

@app.route("/api/save-strategy", methods=["POST"])
def save_strategy():
    data = request.json
    logger.debug("save_strategy called with %s", data)
    try:
        socketio.emit('notification', {'message': '전략 설정 저장'})
        logger.info("Strategy settings saved: %s", json.dumps(data, ensure_ascii=False))
        return jsonify(result="success", message="전략 설정 저장 완료")
    except Exception as e:
        notify_error(f"전략 설정 저장 실패: {e}", "E008")
        return jsonify(result="error", message="전략 저장 실패"), 500

@app.route("/api/run-analysis", methods=["POST"])
def run_analysis():
    data = request.json
    logger.debug("run_analysis called with %s", data)
    try:
        socketio.emit('notification', {'message': 'AI 분석을 실행했습니다.'})
        logger.info("AI analysis started")
        return jsonify(result="success", message="AI 분석 시작")
    except Exception as e:
        notify_error(f"AI 분석 실행 실패: {e}", "E009")
        return jsonify(result="error", message="분석 실행 실패"), 500

@app.route("/api/manual-sell", methods=["POST"])
def manual_sell():
    data = request.get_json(silent=True) or {}
    coin = data.get('coin')
    logger.debug("manual_sell called for %s", coin)
    try:
        if not coin:
            raise ValueError("Invalid coin")
        socketio.emit('notification', {'message': f'{coin} 수동 매도 요청'})
        global positions, alerts
        positions = [p for p in positions if p['coin'] != coin]
        alerts.insert(0, {"time": datetime.now().strftime('%H:%M'), "message": f"{coin} 매도"})
        socketio.emit('positions', positions)
        socketio.emit('alerts', alerts)
        logger.info("Manual sell executed for %s", coin)
        return jsonify(result="success", message="시장가로 매도가 주문 되었습니다.")
    except Exception as e:
        notify_error(f"수동 매도 실패: {e}", "E010")
        return jsonify(result="error", message=f"매도 취소: {e}"), 500

@app.route("/api/manual-buy", methods=["POST"])
def manual_buy():
    data = request.get_json(silent=True) or {}
    coin = data.get('coin')
    logger.debug("manual_buy called for %s", coin)
    try:
        if not coin:
            raise ValueError("Invalid coin")
        socketio.emit('notification', {'message': f'{coin} 수동 매수 요청'})
        global positions, alerts
        positions.append({
            "coin": coin,
            "pnl": 0,
            "entry": 50,
            "trend": 50,
            "trend_color": "green",
            "signal": "sell-wait",
            "signal_label": "관망",
        })
        alerts.insert(0, {"time": datetime.now().strftime('%H:%M'), "message": f"{coin} 매수"})
        socketio.emit('positions', positions)
        socketio.emit('alerts', alerts)
        logger.info("Manual buy executed for %s", coin)
        return jsonify(result="success", message=f"{coin} 매수 요청")
    except Exception as e:
        notify_error(f"수동 매수 실패: {e}", "E011")
        return jsonify(result="error", message="수동 매수 실패"), 500

@app.route("/api/exclude-coin", methods=["POST"])
def exclude_coin():
    data = request.get_json(silent=True) or {}
    coin = data.get('coin')
    logger.debug("exclude_coin called for %s", coin)
    try:
        if not coin:
            raise ValueError("Invalid coin")
        if not any(c['coin'] == coin for c in excluded_coins):
            excluded_coins.append({
                "coin": coin,
                "deleted": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            })
            save_excluded()
        return jsonify(result="success", message=f"{coin} 제외됨")
    except Exception as e:
        notify_error(f"제외 실패: {e}", "E012")
        return jsonify(result="error", message="제외 실패"), 500

@app.route("/api/restore-coin", methods=["POST"])
def restore_coin():
    data = request.get_json(silent=True) or {}
    coin = data.get('coin')
    logger.debug("restore_coin called for %s", coin)
    try:
        if not coin:
            raise ValueError("Invalid coin")
        global excluded_coins
        new_list = [c for c in excluded_coins if c.get('coin') != coin]
        if len(new_list) != len(excluded_coins):
            excluded_coins = new_list
            save_excluded()
        return jsonify(result="success", message=f"{coin} 복구됨")
    except Exception as e:
        notify_error(f"복구 실패: {e}", "E013")
        return jsonify(result="error", message="복구 실패"), 500

@app.route("/api/excluded-coins", methods=["GET"])
def get_excluded_coins():
    logger.debug("get_excluded_coins called")
    try:
        return jsonify(result="success", coins=excluded_coins)
    except Exception as e:
        notify_error(f"조회 실패: {e}", "E014")
        return jsonify(result="error", message="조회 실패"), 500

@app.route("/api/balances", methods=["GET"])
def api_balances():
    """Return current balances for the dashboard."""
    logger.debug("api_balances called")
    try:
        data = get_balances()
        ex_ids = {c['coin'] for c in excluded_coins} if excluded_coins else None
        positions = trader.build_positions(data, ex_ids) if data else []
        logger.info("Balance check success")
        return jsonify(result="success", balances=positions)
    except Exception as e:
        notify_error(f"잔고 조회 실패: {e}", "E015")
        return jsonify(result="error", message="잔고 조회 실패"), 500

@app.route("/api/signals", methods=["GET"])
def api_signals():
    """Return current buy signals for the dashboard."""
    logger.debug("api_signals called")
    try:
        signals = get_filtered_signals()
        coins = [s.get("coin") for s in signals]
        logger.info("[MONITOR] 모니터링 대상 %s", coins if coins else "없음")
        logger.info("Signal check success")
        return jsonify(result="success", signals=signals)
    except Exception as e:
        notify_error(f"시그널 조회 실패: {e}", "E016")
        return jsonify(result="error", message="시그널 조회 실패"), 500


@app.route("/api/status", methods=["GET"])
def api_status():
    """Return bot running status and last update."""
    logger.debug("api_status called")
    try:
        return jsonify(result="success", status=get_status())
    except Exception as e:
        notify_error(f"상태 조회 실패: {e}", "E017")
        return jsonify(result="error", message="상태 조회 실패"), 500


@app.route("/api/account", methods=["GET"])
def api_account():
    """Return latest account summary."""
    logger.debug("api_account called")
    try:
        summary = get_account_summary()
        return jsonify(result="success", account=summary)
    except Exception as e:
        notify_error(f"계좌 조회 실패: {e}", "E018")
        return jsonify(result="error", message="계좌 조회 실패"), 500


@app.route("/save", methods=["POST"])
def save():
    """Save posted JSON data to file."""
    data = request.get_json(silent=True)
    logger.debug("save called with %s", data)
    if data is None:
        return jsonify(result="error", message="Invalid JSON"), 400
    try:
        os.makedirs("config", exist_ok=True)
        with open("config/user_data.json", "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        socketio.emit('notification', {'message': '설정이 저장되었습니다.'})
        logger.info("User data saved: %s", json.dumps(data, ensure_ascii=False))
        update_timestamp()
        status = get_status()
        return jsonify(result="success", status=status)
    except Exception as e:
        notify_error(f"저장 실패: {e}", "E019")
        return jsonify(result="error", message="저장 실패"), 500

@socketio.on('refresh')
def handle_refresh(data):
    logger.debug("handle_refresh called")
    try:
        socketio.emit('positions', positions)
        socketio.emit('alerts', alerts)
    except Exception as e:
        notify_error(f"리프레시 실패: {e}", "E020")

@app.route("/download-code")
def download_code():
    logger.debug("download_code called")
    try:
        base = os.path.abspath(os.path.dirname(__file__))
        zip_path = os.path.join(base, "upbit_bot_project.zip")
        if os.path.exists(zip_path):
            os.remove(zip_path)
        shutil.make_archive("upbit_bot_project", 'zip', base)
        logger.info("Project code zipped")
        return send_file(zip_path, as_attachment=True)
    except Exception as e:
        notify_error(f"코드 다운로드 실패: {e}", "E021")
        return jsonify(result="error", message="다운로드 실패"), 500

if __name__ == "__main__":
    socketio.run(app, debug=True)
