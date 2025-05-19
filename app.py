"""
UPBIT 5분봉 자동매매 Flask 메인 앱 (초보자 상세 주석)
"""
from flask import Flask, render_template, jsonify, request, send_file
from flask_socketio import SocketIO
import os, shutil, logging, json  # 기본 모듈들
from datetime import datetime

app = Flask(__name__)  # Flask 애플리케이션 생성
socketio = SocketIO(app, cors_allowed_origins="*")  # 실시간 알림용 SocketIO

# 로그 설정
logging.basicConfig(
    filename='logs/bot_debug.log', level=logging.DEBUG,
    format='[%(levelname)s][%(asctime)s] %(message)s'
)
logger = logging.getLogger("bot")

# 샘플 설정 로드
with open("config/config.json", encoding="utf-8") as f:
    config = json.load(f)
with open("config/secrets.json", encoding="utf-8") as f:
    secrets = json.load(f)

# 전역 변수 (설정 예시)
settings = {"running": False, "strategy": "M-BREAK", "TP": 0.02, "SL": 0.01,
            "funds": 1000000,
            "max_amount": 500000,
            "buy_amount": 100000,
            "max_positions": 5,
            "slippage": 0.1,
            "balance_action": "alert",
            "run_time": "09:00-22:00",
            "rebalance": "1d",
            "event_stop": "",
            "backtest": "OFF",
            "candle": "5m",
            "fee": 0.05,
            "tune": "",
            "ai_opt": "OFF",
            "exchange": "UPBIT",
            "tg_on": True,
            "events": ["BUY", "SELL", "STOP"],
            "notify_from": "08:00",
            "notify_to": "22:00",
            "updated": "2025-05-18"}

with open('config/config.json', encoding='utf-8') as f:
    config_data = json.load(f)
with open('config/secrets.json', encoding='utf-8') as f:
    secrets_data = json.load(f)

positions = [
    {"coin": "BTC", "entry": 48, "trend": 66, "trend_color": "green", "signal": "sell-max", "signal_label": "수익 극대화"},
]
signals = [
    {"coin": "BTC", "trend": "🔼", "volatility": "🔵 5.8", "volume": "⏫ 250", "strength": "⏫ 122", "gc": "🔼", "rsi": "⏫ E", "signal": "강제 매수", "signal_class": "go", "key": "MBREAK"},
]
alerts = [
    {"time": "14:20", "message": "BTC 매수 체결 (+2.1%)"},
    {"time": "14:05", "message": "ETH 손절 (-2.9%)"},
]
history = [
    {"time": "2025-05-18 13:00", "label": "적용", "cls": "success"},
    {"time": "2025-05-17 10:13", "label": "분석", "cls": "primary"},
]
buy_results = signals
sell_results = signals
strategies = [
    {"name": "M-BREAK", "key": "MBREAK", "enabled": True, "tp": 0.02, "sl": 0.01, "trail": 0.012, "option": "ATR≥0.035", "recommend": "TP2% SL1%", "desc": "강한 추세 돌파"},
    {"name": "P-PULL", "key": "PPULL", "enabled": False, "tp": 0.025, "sl": 0.012, "trail": 0.015, "option": "조정 매수", "recommend": "TP2.5%", "desc": "풀백 매수"},
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
    return render_template("index.html", running=settings["running"], positions=positions, alerts=alerts, signals=signals, updated=settings["updated"])

@app.route("/strategy")
def strategy_page():
    return render_template("strategy.html", strategies=strategies, settings=settings)

# AI 전략 분석 페이지
@app.route("/ai-analysis")
def ai_analysis_page():
    return render_template(
        "ai_analysis.html",
        buy_results=buy_results,
        sell_results=sell_results,
        history=history,
        strategies=analysis_strategies,
    )

@app.route("/risk")
def risk_page():
    risk = {
        "daily": 2, "weekly": 5, "monthly": 10,
        "push": True, "telegram": True,
        "force_pct": 5, "force_count": 3,
        "cont_loss": 4, "cont_profit": 5,
        "log_path": "logs/trades.csv", "updated": settings["updated"]
    }
    return render_template("risk.html", risk=risk)

@app.route("/notifications")
def notifications_page():
    return render_template("notifications.html", alerts=alerts, alert_config=config_data.get("alerts", {}))

@app.route("/funds")
def funds_page():
    return render_template("funds.html", settings=settings)

@app.route("/settings")
def settings_page():
    return render_template("settings.html", settings=settings, secrets=secrets_data)

@app.route("/api/start-bot", methods=["POST"])
def start_bot():
    logger.info("[API] 봇 시작 요청")
    settings["running"] = True
    socketio.emit('notification', {'message': '봇이 시작되었습니다.'})
    return jsonify(result="success", message="봇이 시작되었습니다.")

@app.route("/api/stop-bot", methods=["POST"])
def stop_bot():
    logger.info("[API] 봇 중지 요청")
    settings["running"] = False
    socketio.emit('notification', {'message': '봇이 정지되었습니다.'})
    return jsonify(result="success", message="봇이 정지되었습니다.")

@app.route("/api/apply-strategy", methods=["POST"])
def apply_strategy():
    # 실제 전략 설정 코드 (생략)
    data = request.json
    logger.info(f"[API] 전략 적용: {data}")
    settings["strategy"] = data.get("strategy", "M-BREAK")
    socketio.emit('notification', {'message': '전략이 적용되었습니다.'})
    return jsonify(result="success", message="전략이 적용되었습니다.")

@app.route("/api/save-settings", methods=["POST"])
def save_settings():
    settings.update(request.json)
    socketio.emit('notification', {'message': '설정이 저장되었습니다.'})
    return jsonify(result="success", message="저장 완료")

@app.route("/api/save-risk", methods=["POST"])
def save_risk():
    socketio.emit('notification', {'message': '리스크 설정 저장'})
    return jsonify(result="success", message="리스크 저장 완료")

@app.route("/api/save-alerts", methods=["POST"])
def save_alerts():
    socketio.emit('notification', {'message': '알림 설정 저장'})
    return jsonify(result="success", message="알림 설정 저장 완료")

@app.route("/api/save-funds", methods=["POST"])
def save_funds():
    settings.update(request.json)
    socketio.emit('notification', {'message': '자금 설정 저장'})
    return jsonify(result="success", message="자금 설정 저장 완료")

@app.route("/api/save-strategy", methods=["POST"])
def save_strategy():
    socketio.emit('notification', {'message': '전략 설정 저장'})
    return jsonify(result="success", message="전략 설정 저장 완료")

@app.route("/api/run-analysis", methods=["POST"])
def run_analysis():
    socketio.emit('notification', {'message': 'AI 분석을 실행했습니다.'})
    return jsonify(result="success", message="AI 분석 시작")

@app.route("/api/manual-sell", methods=["POST"])
def manual_sell():
    coin = request.json.get('coin')
    socketio.emit('notification', {'message': f'{coin} 수동 매도 요청'})
    global positions, alerts
    positions = [p for p in positions if p['coin'] != coin]
    alerts.insert(0, {"time": datetime.now().strftime('%H:%M'), "message": f"{coin} 매도"})
    socketio.emit('positions', positions)
    socketio.emit('alerts', alerts)
    return jsonify(result="success", message=f"{coin} 매도 요청" )

@app.route("/api/manual-buy", methods=["POST"])
def manual_buy():
    coin = request.json.get('coin')
    socketio.emit('notification', {'message': f'{coin} 수동 매수 요청'})
    global positions, alerts
    positions.append({"coin": coin, "entry": 50, "trend": 50, "trend_color": "green",
                      "signal": "sell-wait", "signal_label": "관망"})
    alerts.insert(0, {"time": datetime.now().strftime('%H:%M'), "message": f"{coin} 매수"})
    socketio.emit('positions', positions)
    socketio.emit('alerts', alerts)
    return jsonify(result="success", message=f"{coin} 매수 요청")

@socketio.on('refresh')
def handle_refresh(data):
    socketio.emit('positions', positions)
    socketio.emit('alerts', alerts)

@app.route("/download-code")
def download_code():
    # 전체 프로젝트 디렉토리 압축 후 파일 제공
    base = os.path.abspath(os.path.dirname(__file__))
    zip_path = os.path.join(base, "upbit_bot_project.zip")
    if os.path.exists(zip_path):
        os.remove(zip_path)
    shutil.make_archive("upbit_bot_project", 'zip', base)
    return send_file(zip_path, as_attachment=True)

if __name__ == "__main__":
    socketio.run(app, debug=True)
