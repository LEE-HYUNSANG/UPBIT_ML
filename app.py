"""
UPBIT 5분봉 자동매매 Flask 메인 앱 (초보자 상세 주석)
"""
from flask import Flask, render_template, jsonify, request, send_file
from flask_socketio import SocketIO
import os
import shutil
import logging
import json  # 기본 모듈들
import requests
from datetime import datetime, timedelta

from utils import (
    load_secrets,
    send_telegram,
    setup_logging,
    calc_tis,
    load_filter_settings,
)
from bot.trader import UpbitTrader
from bot.runtime_settings import settings, load_from_file
from helpers.logger import log_trade, get_recent_logs
import pyupbit
import threading
import time
import pandas as pd
import talib as ta

app = Flask(__name__)  # Flask 애플리케이션 생성
socketio = SocketIO(app, cors_allowed_origins="*")  # 실시간 알림용 SocketIO

# 로그 설정 (파일 + 콘솔)
logger = setup_logging(level="DEBUG", log_dir="logs")

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
FILTER_FILE = "config/filter.json"
filter_config = load_filter_settings(FILTER_FILE)

# 전략 설정 파일 경로
STRATEGY_FILE = "config/strategy.json"
DEFAULT_STRATEGY_FILE = "config/default_strategy.json"
from helpers.utils.strategy_cfg import load_strategy_list, save_strategy_list, restore_defaults
# 서버 시작 시 전략 목록 로드
strategy_table = load_strategy_list(STRATEGY_FILE)

SIGNAL_ORDER = {
    "buy-strong": 0,
    "buy": 1,
    "wait": 2,
    "avoid": 3,
    "ban": 4,
    "nodata": 5,
}


def sort_results_and_coins(results: list[dict], coins: list[dict]) -> tuple[list[dict], list[dict]]:
    """신호 우선순위와 24시간 거래대금으로 정렬한다."""
    vol_map = {c["coin"]: c.get("volume", 0) for c in coins}
    pairs = list(zip(results, coins))
    pairs.sort(
        key=lambda p: (
            SIGNAL_ORDER.get(p[0].get("signal_class"), len(SIGNAL_ORDER)),
            -vol_map.get(p[0].get("coin"), 0),
        )
    )
    sorted_results = [p[0] for p in pairs]
    sorted_coins = [p[1] for p in pairs]
    return sorted_results, sorted_coins

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

def notify(message: str) -> None:
    """브라우저와 텔레그램으로 메시지를 전송한다."""
    logger.debug("[NOTIFY] %s", message)
    socketio.emit('notification', {'message': message})
    token = secrets.get("TELEGRAM_TOKEN")
    chat_id = secrets.get("TELEGRAM_CHAT_ID")
    if config.get("alerts", {}).get("telegram") and token and chat_id:
        send_telegram(token, chat_id, message)

def notify_error(message: str, code: str) -> None:
    """에러 코드를 포함해 로그와 알림을 전송한다."""
    full = f"[{code}] {message}"
    logger.error(full)
    notify(full)

def emit_refresh_event() -> None:
    """1초 간격으로 세 번 refresh_data SocketIO 이벤트를 발생시킨다."""
    logger.debug("[SOCKET] emit_refresh_event")
    def _emit():
        for _ in range(3):
            logger.debug("[SOCKET] emit refresh_data")
            socketio.emit("refresh_data")
            time.sleep(1)

    threading.Thread(target=_emit, daemon=True).start()

def get_balances():
    """트레이더에서 현재 코인 잔고를 가져온다."""
    logger.debug("Fetching balances")
    data = trader.get_balances()
    if data is None:
        return []
    if excluded_coins:
        ex_ids = {c['coin'] for c in excluded_coins}
        data = [b for b in data if b.get('currency') not in ex_ids]
    return data


def get_status() -> dict:
    """봇 실행 상태와 다음 갱신 시각을 포함한 상태를 반환한다."""
    logger.debug("Fetching status")
    return {
        "running": settings.running,
        "updated": settings.updated,
        "next_refresh": next_refresh,
    }


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
    """설정 변경 시각을 갱신한다."""
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

# Buy monitor signal cache
_signal_lock = threading.Lock()
signal_cache: list[dict] = []

# 다음 갱신 예정 시각
next_refresh: str | None = None


def save_market_file(data: list[dict]) -> None:
    """가져온 시세 데이터를 ``MARKET_FILE`` 에 저장한다."""
    os.makedirs(os.path.dirname(MARKET_FILE), exist_ok=True)
    with open(MARKET_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def update_monitor_list() -> None:
    """대시보드 필터를 적용해 모니터링 목록을 저장한다.

    한 번 생성된 목록은 파일로 보관하여 이후 조회 시 그대로 사용한다.
    """
    global signal_cache
    signals = get_filtered_signals()
    results = []
    for s in signals:
        ticker = f"KRW-{s['coin']}"
        results.append(calc_buy_signal_retry(ticker, s["coin"]))

    results, signals = sort_results_and_coins(results, signals)

    os.makedirs(os.path.dirname(MONITOR_FILE), exist_ok=True)
    with open(MONITOR_FILE, "w", encoding="utf-8") as f:
        json.dump(signals, f, ensure_ascii=False, indent=2)
    logger.debug("[MARKET] Monitor list saved %d coins", len(signals))

    with _signal_lock:
        signal_cache = results
    logger.debug("[MARKET] Signal cache primed %d coins", len(results))


def refresh_market_data() -> None:
    """업비트에서 원화 마켓 시세와 24시간 거래대금을 가져온다."""
    global market_cache
    try:
        tickers = pyupbit.get_tickers(fiat="KRW")
        url = "https://api.upbit.com/v1/ticker?markets=" + ",".join(tickers)
        resp = requests.get(url, timeout=5)
        resp.raise_for_status()
        tick_data = resp.json()
        data = []
        for item in tick_data:
            price = float(item.get("trade_price", 0))
            vol = float(item.get("acc_trade_price_24h", 0))
            market = item.get("market", "")
            logger.debug("[MARKET] fetched %s price=%.8f vol=%.2f", market, price, vol)
            data.append({"coin": market.split("-")[-1], "price": price, "volume": vol})
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
        # 모니터링 코인 목록은 설정 변경 시에만 갱신한다
    except Exception as e:
        logger.exception("Market data fetch failed: %s", e)


def refresh_market_data_retry(retries: int = 3, delay: float = 0.2) -> None:
    """시세 데이터가 없을 경우 재시도한다."""
    for i in range(retries):
        refresh_market_data()
        with _market_lock:
            if market_cache:
                return
        logger.debug("[MARKET] retry %d due to empty data", i + 1)
        time.sleep(delay)


def calc_buy_signal(ticker: str, coin: str) -> dict:
    """매수 모니터링 지표를 계산해 반환한다."""
    logger.cal("[BUY MON] calc_buy_signal for %s", ticker)
    entry = {
        "coin": coin,
        "price": "⛔",
        "trend": "⛔",
        "volatility": "⛔",
        "volume": "⛔",
        "strength": "⛔",
        "gc": "⛔",
        "rsi": "⛔",
        "signal": "데이터 대기",
        "signal_class": "nodata",
    }
    try:
        df = pyupbit.get_ohlcv(ticker, interval="minute5", count=60)
        if df is None or df.empty:
            return entry
        price = pyupbit.get_current_price(ticker) or float(df["close"].iloc[-1])
        entry["price"] = round(float(price), 2)
        df = df.iloc[:-1]
        if df.empty:
            return entry

        ema5 = df["close"].ewm(span=5).mean()
        ema20 = df["close"].ewm(span=20).mean()
        ema60 = df["close"].ewm(span=60).mean()
        slope20 = ema20.pct_change()
        up = (ema5 > ema20) & (ema20 > ema60) & (slope20 > 0)
        down = (ema5 < ema20) & (ema20 < ema60) & (slope20 < 0)
        side = slope20.abs() < 0.0005
        if up.iloc[-1]:
            trend = "U"; entry["trend"] = "<span class='trend-up'>🔼</span>"
        elif down.iloc[-1]:
            trend = "D"; entry["trend"] = "<span class='trend-down'>🔻</span>"
        elif side.iloc[-1]:
            trend = "S"; entry["trend"] = "<span class='trend-side'>🔸</span>"
        else:
            trend = "F"; entry["trend"] = "<span class='trend-side'>🔸</span>"

        atr = ta.ATR(df["high"], df["low"], df["close"], 14)
        atr_pct = atr.iloc[-1] / df["close"].iloc[-1] * 100
        if atr_pct >= 5:
            entry["volatility"] = f"🔵 {atr_pct:.1f}%"
        elif atr_pct >= 1:
            entry["volatility"] = f"🟡 {atr_pct:.1f}%"
        else:
            entry["volatility"] = f"🔻 {atr_pct:.1f}%"

        vol_ratio = df["volume"].iloc[-1] / (df["volume"].rolling(20).mean().iloc[-1] or 1)
        if vol_ratio >= 2:
            entry["volume"] = f"⏫ {vol_ratio:.2f}"
        elif vol_ratio >= 1.1:
            entry["volume"] = f"🔼 {vol_ratio:.2f}"
        elif vol_ratio >= 0.7:
            entry["volume"] = f"🔸 {vol_ratio:.2f}"
        else:
            entry["volume"] = f"🔻 {vol_ratio:.2f}"

        tis = calc_tis(ticker)

        if ticker.endswith("-XPR"):
            logger.info("[TIS] %s %.2f", ticker, tis if tis is not None else -1)

        if tis is not None:
            if tis >= 120:
                entry["strength"] = f"⏫ {tis:.0f}"
            elif tis >= 105:
                entry["strength"] = f"🔼 {tis:.0f}"
            elif tis >= 95:
                entry["strength"] = f"🔸 {tis:.0f}"
            else:
                entry["strength"] = f"🔻 {tis:.0f}"
        else:
            logger.cal("[BUY MON] TIS not available for %s", ticker)

        gc = (ema5.shift(1) < ema20.shift(1)) & (ema5 > ema20)
        dc = (ema5.shift(1) > ema20.shift(1)) & (ema5 < ema20)
        if gc.iloc[-1]:
            entry["gc"] = "<span class='gc'>🔼</span>"
        elif dc.iloc[-1]:
            entry["gc"] = "<span class='dc'>🔻</span>"
        else:
            entry["gc"] = "<span class='gc-neutral'>🔸</span>"

        rsi_val = ta.RSI(df["close"], 14).iloc[-1]
        if rsi_val < 30:
            ris_code = "E"; entry["rsi"] = "<span class='rsi-e'>⏫</span>"
        elif rsi_val < 40:
            ris_code = "S"; entry["rsi"] = "<span class='rsi-s'>🔼</span>"
        elif rsi_val < 70:
            ris_code = "N"; entry["rsi"] = "<span class='rsi-n'>🔸</span>"
        elif rsi_val < 80:
            ris_code = "B"; entry["rsi"] = "<span class='rsi-b'>🔻</span>"
        else:
            ris_code = "X"; entry["rsi"] = "<span class='rsi-x'>🔻</span>"

        score = (
            (trend == "U") * 25
            + (atr_pct >= 5) * 15
            + ((atr_pct >= 1) and (atr_pct < 5)) * 10
            + (vol_ratio >= 2) * 15
            + (vol_ratio >= 1.1) * 10
            + (tis is not None and tis >= 120) * 15
            + (tis is not None and tis >= 105) * 10
            + gc.iloc[-1] * 5
            + (ris_code == "E") * 5
            + (ris_code == "S") * 3
        )

        if vol_ratio < 0.7 or (tis is not None and tis < 95):
            entry["signal"] = "매수 금지"
            entry["signal_class"] = "ban"
        elif trend == "D" or ris_code in ("B", "X"):
            entry["signal"] = "매수 회피"
            entry["signal_class"] = "avoid"
        elif trend == "U" and (tis or 0) >= 120 and ris_code in ("E", "S") and vol_ratio >= 2:
            entry["signal"] = "매수 적극 추천"
            entry["signal_class"] = "buy-strong"
        elif trend == "U" and (tis or 0) >= 105 and vol_ratio >= 1.1 and ris_code not in ("B", "X"):
            entry["signal"] = "매수 추천"
            entry["signal_class"] = "buy"
        else:
            entry["signal"] = "관망"
            entry["signal_class"] = "wait"

        logger.cal(
            "[BUY MON] %s price=%s trend=%s atr=%.2f vol=%.2f tis=%s gc=%s rsi=%.2f signal=%s",
            ticker,
            entry["price"],
            trend,
            atr_pct,
            vol_ratio,
            tis,
            "GC" if gc.iloc[-1] else "DC" if dc.iloc[-1] else "N",
            rsi_val,
            entry["signal"],
        )

    except Exception as e:
        logger.warning("[BUY MON] indicator error %s: %s", ticker, e)
    return entry


def get_latest_5m_close(ticker: str) -> str | None:
    """지정 티커의 최근 5분봉 종료 시각을 반환한다."""
    try:
        df = pyupbit.get_ohlcv(ticker, interval="minute5", count=1)
        if df is not None and not df.empty:
            return df.index[-1].strftime("%Y-%m-%dT%H:%M:%S")
    except Exception as e:
        logger.debug("get_latest_5m_close error %s: %s", ticker, e)
    return None


def calc_buy_signal_retry(ticker: str, coin: str, retries: int = 3) -> dict:
    """지표 계산 후 데이터가 없으면 재시도한다."""
    for i in range(retries):
        entry = calc_buy_signal(ticker, coin)
        missing = [
            k
            for k in (
                "price",
                "trend",
                "volatility",
                "volume",
                "strength",
                "gc",
                "rsi",
            )
            if entry.get(k) == "⛔"
        ]
        if not missing:
            return entry
        logger.cal("[BUY MON] retry %d for %s missing %s", i + 1, ticker, missing)
        time.sleep(0.2)
    logger.cal("[BUY MON] final entry for %s after retries", ticker)
    return entry


def market_refresh_loop() -> None:
    """시세 데이터를 주기적으로 갱신한다."""
    global next_refresh
    prev_close = None
    while True:
        close_time = get_latest_5m_close("KRW-BTC")
        if close_time and close_time != prev_close:
            refresh_market_data_retry()
            prev_close = close_time
            try:
                dt = datetime.fromisoformat(close_time) + timedelta(minutes=5)
                next_refresh = dt.strftime("%Y-%m-%dT%H:%M:%S")
            except Exception:
                next_refresh = None
            emit_refresh_event()
        time.sleep(10)


def buy_signal_monitor_loop() -> None:
    """매수 모니터링 신호를 주기적으로 계산한다."""
    global signal_cache, next_refresh
    prev_close = None
    retry_deadline = None
    while True:
        try:
            with open(MONITOR_FILE, "r", encoding="utf-8") as f:
                coins = json.load(f)
        except Exception:
            coins = []
        if not coins:
            time.sleep(10)
            continue
        ref_ticker = f"KRW-{coins[0]['coin']}"
        close_time = get_latest_5m_close(ref_ticker)
        if close_time and close_time != prev_close:
            results = []
            for c in coins:
                ticker = f"KRW-{c['coin']}"
                results.append(calc_buy_signal_retry(ticker, c["coin"]))

            results, coins = sort_results_and_coins(results, coins)
            with _signal_lock:
                signal_cache = results
            logger.debug("[BUY MONITOR] updated %d signals at %s", len(results), close_time)
            prev_close = close_time
            try:
                dt = datetime.fromisoformat(close_time) + timedelta(minutes=5)
                next_refresh = dt.strftime("%Y-%m-%dT%H:%M:%S")
                retry_deadline = dt - timedelta(seconds=10)
            except Exception:
                next_refresh = None
                retry_deadline = None
            emit_refresh_event()
        elif retry_deadline and datetime.now() < retry_deadline:
            updated = False
            with _signal_lock:
                results = list(signal_cache)
            result_map = {r["coin"]: r for r in results}
            for c in coins:
                ticker = f"KRW-{c['coin']}"
                entry = result_map.get(c['coin'])
                keys = ("price", "trend", "volatility", "volume", "strength", "gc", "rsi")
                if entry and any(entry.get(k) == "⛔" for k in keys):
                    new_entry = calc_buy_signal_retry(ticker, c["coin"])
                    if new_entry != entry:
                        result_map[c['coin']] = new_entry
                        updated = True
            if updated:
                results = list(result_map.values())
                results, coins = sort_results_and_coins(results, coins)
                with _signal_lock:
                    signal_cache = results
                logger.debug("[BUY MONITOR] partial refresh")
                emit_refresh_event()
        time.sleep(10)

def get_filtered_signals():
    """가격 범위와 거래대금 순위로 필터링한 시세 데이터를 반환한다."""
    logger.info("[MONITOR] 매수 모니터링 요청")
    logger.cal("[MONITOR] 필터 조건 %s", filter_config)
    min_p = float(filter_config.get("min_price", 0) or 0)
    max_p = float(filter_config.get("max_price", 0) or 0)
    rank = int(filter_config.get("rank", 0) or 0)
    with _market_lock:
        data = list(market_cache)

    filtered = []
    for s in data:
        logger.cal("[MONITOR] 원본 시그널 %s", s)
        price = s["price"]
        if min_p and price < min_p:
            logger.cal(
                "[MONITOR] 제외 %s price %.8f < min_price %.8f",
                s["coin"],
                price,
                min_p,
            )
            continue
        if max_p and max_p > 0 and price > max_p:
            logger.cal(
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
        logger.cal(
            "[MONITOR] 선정 %s price %.8f rank %d",
            entry["coin"],
            s["price"],
            s["rank"],
        )
        result.append(entry)

    logger.info("[MONITOR] UPBIT 응답 %d개", len(result))
    for s in result:
        logger.cal("[MONITOR] 응답 데이터 %s", s)
    return result

def get_filtered_tickers() -> list[str]:
    """대시보드 조건에 맞는 KRW 티커 목록을 반환한다."""
    logger.cal("Filtering tickers with %s", filter_config)
    signals = get_filtered_signals()
    tickers = [f"KRW-{s['coin']}" for s in signals]
    logger.cal("Filtered tickers: %s", tickers)
    return tickers


def _reload_filter_periodically() -> None:
    """filter.json을 주기적으로 다시 읽어 설정을 갱신한다."""
    global filter_config
    while True:
        socketio.sleep(300)
        new_cfg = load_filter_settings(FILTER_FILE)
        if new_cfg != filter_config:
            filter_config = new_cfg
            update_monitor_list()
            logger.info("[FILTER] reloaded %s", new_cfg)


# Initial data load and background threads
refresh_market_data()
initial_close = get_latest_5m_close("KRW-BTC")
if initial_close:
    try:
        dt = datetime.fromisoformat(initial_close) + timedelta(minutes=5)
        next_refresh = dt.strftime("%Y-%m-%dT%H:%M:%S")
    except Exception:
        next_refresh = None
update_monitor_list()
threading.Thread(target=market_refresh_loop, daemon=True).start()
threading.Thread(target=buy_signal_monitor_loop, daemon=True).start()
socketio.start_background_task(_reload_filter_periodically)

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
        "desc": "고변동·거래량 급증 구간에서 전고 돌파 추격",
        "win": 75,
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
        "desc": "상승장 조정 시 EMA50 지지 반등 노림",
        "win": 63,
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
        "desc": "강추세 지속 구간에서 EMA20 눌림 재진입",
        "win": 76,
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
        "desc": "장기 박스권 하단 지지와 과매도 반등",
        "win": 60,
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
        "desc": "급락 후 거래량 폭증 시 V자 반등 노림",
        "win": 65,
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
        "desc": "EMA50/200 골든크로스 후 첫 눌림",
        "win": 74,
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
        "desc": "ATR·거래량 폭발 후 상단 돌파",
        "win": 68,
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
        "desc": "EMA 다중 정렬과 ADX 강세 활용",
        "win": 78,
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
        "desc": "상승 추세 중 VWAP 지지 반등 공략",
        "win": 72,
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


@app.route("/dashboard")
def realtime_dashboard():
    """실시간 로그와 포지션을 모니터링하는 페이지를 렌더링한다."""
    logger.debug("Render real-time dashboard")
    return render_template("dashboard.html")

@app.route("/strategy")
def strategy_page():
    logger.debug("Render strategy page")
    return render_template(
        "strategy.html",
        strategies=strategies,
        analysis_strategies=analysis_strategies,
        settings=settings,
    )

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
def funds():
    logger.debug("Render funds page")
    return render_template("funds.html")


@app.route("/api/funds", methods=["GET"])
def api_get_funds():
    from helpers.utils.funds import load_fund_settings
    return jsonify(load_fund_settings())


@app.route("/api/funds", methods=["POST"])
def api_post_funds():
    from helpers.utils.funds import save_fund_settings
    data = request.get_json(force=True)
    save_fund_settings(data)
    return jsonify({"status": "ok"})

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
        msg = (
            f"봇 시작: 전략 {settings.strategy}, "
            f"1회 매수 {settings.buy_amount:,}원, 최대 {settings.max_positions}종목"
        )
        notify(msg)
        log_trade("bot", {"action": "start"})
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
        notify('봇이 정지되었습니다. 자동 주문이 중단되었습니다.')
        log_trade("bot", {"action": "stop"})
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
        notify(f'전략 적용: {settings.strategy}')
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
        changes = []
        for k in ("min_price", "max_price", "rank"):
            if k in data:
                value = data[k]
                if value in (None, ""):
                    continue
                try:
                    new_val = int(value) if k == "rank" else float(value)
                except (ValueError, TypeError):
                    raise ValueError(f"Invalid value for {k}")
                old_val = filter_config.get(k)
                if old_val != new_val:
                    changes.append(f"{k}: {old_val} → {new_val}")
                filter_config[k] = new_val
        for k, v in data.items():
            if k in ("min_price", "max_price", "rank"):
                continue
            if hasattr(settings, k):
                old = getattr(settings, k)
                if old != v:
                    changes.append(f"{k}: {old} → {v}")
                setattr(settings, k, v)
        os.makedirs(os.path.dirname(FILTER_FILE), exist_ok=True)
        with open(FILTER_FILE, "w", encoding="utf-8") as f:
            json.dump(filter_config, f, ensure_ascii=False, indent=2)
        filter_config.update(load_filter_settings(FILTER_FILE))
        update_monitor_list()
        update_timestamp()
        msg = '설정이 저장되었습니다.'
        if changes:
            msg += '\n' + '\n'.join(changes)
        notify(msg)
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
        details = ', '.join(f'{k}:{v}' for k, v in data.items())
        notify(f'리스크 설정 저장\n{details}')
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
        details = ', '.join(f'{k}:{v}' for k, v in data.items())
        notify(f'알림 설정 저장\n{details}')
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
        details = ', '.join(f'{k}:{v}' for k, v in data.items())
        notify(f'자금 설정 저장\n{details}')
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
        details = ', '.join(f'{k}:{v}' for k, v in data.items())
        notify(f'전략 설정 저장\n{details}')
        logger.info("Strategy settings saved: %s", json.dumps(data, ensure_ascii=False))
        return jsonify(result="success", message="전략 설정 저장 완료")
    except Exception as e:
        notify_error(f"전략 설정 저장 실패: {e}", "E008")
        return jsonify(result="error", message="전략 저장 실패"), 500


@app.route("/api/strategies", methods=["GET"])
def get_strategies():
    logger.debug("get_strategies called")
    return jsonify(strategy_table)


@app.route("/api/strategies", methods=["POST"])
def update_strategies():
    data = request.get_json(force=True)
    logger.debug("update_strategies called with %s", data)
    try:
        if not isinstance(data, list):
            raise ValueError("Invalid data")
        save_strategy_list(data, STRATEGY_FILE)
        global strategy_table
        strategy_table = data
        return jsonify({"status": "ok"})
    except Exception as e:
        notify_error(f"전략 저장 실패: {e}", "E008")
        return jsonify(result="error", message="전략 저장 실패"), 500


@app.route("/api/restore-defaults/strategy", methods=["POST"])
def restore_strategy_defaults_api():
    logger.debug("restore_strategy_defaults_api called")
    try:
        restore_defaults(DEFAULT_STRATEGY_FILE, STRATEGY_FILE)
        global strategy_table
        strategy_table = load_strategy_list(STRATEGY_FILE)
        return jsonify(ok=True)
    except Exception as e:
        notify_error(f"복원 실패: {e}", "E015")
        return jsonify(result="error", message="복원 실패"), 500

@app.route("/api/run-analysis", methods=["POST"])
def run_analysis():
    data = request.json
    logger.debug("run_analysis called with %s", data)
    try:
        notify('AI 분석 실행 요청이 접수되었습니다.')
        logger.info("AI analysis started")
        return jsonify(result="success", message="AI 분석 시작")
    except Exception as e:
        notify_error(f"AI 분석 실행 실패: {e}", "E009")
        return jsonify(result="error", message="분석 실행 실패"), 500

@app.route("/api/manual-sell", methods=["POST"])
def manual_sell():
    """대시보드에서 수동 매도 버튼을 눌렀을 때 호출된다."""
    data = request.get_json(silent=True) or {}
    coin = data.get('coin')
    logger.debug("manual_sell called for %s", coin)
    try:
        if not coin:
            raise ValueError("Invalid coin")
        price = pyupbit.get_current_price(f"KRW-{coin}") or 0
        msg = (
            f'{coin} 수동 매도 요청\n'
            f'주문 가격: {price:,.0f}원\n'
            '주문 방식: 시장가'
        )
        notify(msg)
        log_trade("trade", {"action": "sell", "coin": coin, "price": price})
        socketio.emit('log', {"type": "trade", "action": "sell", "coin": coin, "price": price})
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
    """대시보드에서 수동 매수 버튼을 눌렀을 때 호출된다."""
    data = request.get_json(silent=True) or {}
    coin = data.get('coin')
    logger.debug("manual_buy called for %s", coin)
    try:
        if not coin:
            raise ValueError("Invalid coin")
        price = pyupbit.get_current_price(f"KRW-{coin}") or 0
        amount = settings.buy_amount
        msg = (
            f'{coin} 수동 매수 요청\n'
            f'주문 금액: {amount:,}원\n'
            f'주문 가격: {price:,.0f}원\n'
            '주문 방식: 시장가'
        )
        notify(msg)
        log_trade("trade", {"action": "buy", "coin": coin, "price": price, "amount": amount})
        socketio.emit('log', {"type": "trade", "action": "buy", "coin": coin, "price": price, "amount": amount})
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
    """대시보드에 표시할 현재 잔고 정보를 반환한다."""
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
    """대시보드용 실시간 매수 신호를 반환한다."""
    logger.debug("api_signals called")
    try:
        with _signal_lock:
            signals = list(signal_cache)
        coins = [s.get("coin") for s in signals]
        logger.info("[MONITOR] 모니터링 대상 %s", coins if coins else "없음")
        logger.info("Signal check success")
        return jsonify(result="success", signals=signals)
    except Exception as e:
        notify_error(f"시그널 조회 실패: {e}", "E016")
        return jsonify(result="error", message="시그널 조회 실패"), 500


@app.route("/api/status", methods=["GET"])
def api_status():
    """봇 실행 상태와 최근 갱신 시각을 반환한다."""
    logger.debug("api_status called")
    try:
        return jsonify(result="success", status=get_status())
    except Exception as e:
        notify_error(f"상태 조회 실패: {e}", "E017")
        return jsonify(result="error", message="상태 조회 실패"), 500


@app.route("/api/account", methods=["GET"])
def api_account():
    """가장 최근 계좌 요약 정보를 반환한다."""
    logger.debug("api_account called")
    try:
        summary = get_account_summary()
        return jsonify(result="success", account=summary)
    except Exception as e:
        notify_error(f"계좌 조회 실패: {e}", "E018")
        return jsonify(result="error", message="계좌 조회 실패"), 500


@app.route("/api/logs", methods=["GET"])
def api_logs():
    """최근 트레이드 로그를 반환한다."""
    logger.debug("api_logs called")
    try:
        return jsonify(result="success", logs=get_recent_logs())
    except Exception as e:
        notify_error(f"로그 조회 실패: {e}", "E030")
        return jsonify(result="error", message="로그 조회 실패"), 500


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
        items = ', '.join(f'{k}:{v}' for k, v in data.items())
        notify(f'사용자 설정 저장\n{items}')
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
