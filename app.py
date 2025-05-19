"""
UPBIT 5분봉 자동매매 Flask 메인 앱 (초보자 상세 주석)
"""
from flask import Flask, render_template, jsonify, request, send_file
from flask_socketio import SocketIO
import os, shutil, logging, json

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")

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

@app.route("/")
def dashboard():
    return render_template("index.html", running=settings["running"], positions=positions, alerts=alerts, signals=signals, updated=settings["updated"])

@app.route("/strategy")
def strategy_page():
    return render_template("strategy.html", strategies=strategies, settings=settings)

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
    return render_template("notifications.html", alerts=alerts)

@app.route("/funds")
def funds_page():
    return render_template("funds.html")

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
    return jsonify(result="success", message=f"{coin} 매도 요청" )

@app.route("/api/manual-buy", methods=["POST"])
def manual_buy():
    coin = request.json.get('coin')
    socketio.emit('notification', {'message': f'{coin} 수동 매수 요청'})
    return jsonify(result="success", message=f"{coin} 매수 요청")

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
