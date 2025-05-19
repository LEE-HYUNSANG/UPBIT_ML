"""
UPBIT 5분봉 자동매매 Flask 메인 앱 (초보자 상세 주석)
"""
from flask import Flask, render_template, jsonify, request, send_file
import os, shutil, logging, json

app = Flask(__name__)

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
settings = {"running": False, "strategy": "M-BREAK", "TP": 0.02, "SL": 0.01, "funds": 1000000}

@app.route("/")
def dashboard():
    # 샘플 데이터 전달 (실제 구현 시 DB/로직으로 대체)
    positions = [
        {"coin": "BTC", "stop": 0, "entry": 48, "take": 0, "trend_pct": 66, "trend_color": "green", "sell_signal": "수익 극대화"},
        {"coin": "ETH", "stop": 0, "entry": 37, "take": 0, "trend_pct": 52, "trend_color": "red", "sell_signal": "수익 극대화"},
    ]
    buys = [
        {"coin": "BTC", "trend": "🔼", "volatility": "🔵 5.8", "volume": "⏫ 250", "strength": "⏫ 122", "gc": "🔼", "ris": "⏫ E", "signal": "강제 매수"},
    ]
    alerts = [
        {"time": "14:20", "msg": "BTC 매수 체결 (+2.1 %)"},
        {"time": "14:05", "msg": "ETH 손절 (-2.9 %)"},
    ]
    return render_template(
        "index.html",
        settings=settings,
        config=config,
        positions=positions,
        buys=buys,
        alerts=alerts,
    )

@app.route("/strategy")
def strategy():
    strategies = [
        {"name": "M-BREAK", "enabled": True, "tp": 0.02, "sl": 0.01, "trail": 0.012, "option": "ATR≥0.035, 20봉거래량 1.8x, 전고점돌파", "rec": "TP 2%<br>SL 1%"},
        {"name": "P-PULL", "enabled": False, "tp": "", "sl": "", "trail": "", "option": "RSI≤24, 50EMA 근접", "rec": "-"},
        {"name": "T-FLOW", "enabled": False, "tp": "", "sl": "", "trail": "", "option": "OBV 3봉 상승", "rec": "-"},
        {"name": "B-LOW", "enabled": False, "tp": "", "sl": "", "trail": "", "option": "저점 RSI 반등", "rec": "-"},
        {"name": "V-REV", "enabled": False, "tp": "", "sl": "", "trail": "", "option": "급락 후 반등", "rec": "-"},
        {"name": "G-REV", "enabled": False, "tp": "", "sl": "", "trail": "", "option": "EMA50>200", "rec": "-"},
        {"name": "VOL-BRK", "enabled": False, "tp": "", "sl": "", "trail": "", "option": "ATR 폭발", "rec": "-"},
        {"name": "EMA-STACK", "enabled": False, "tp": "", "sl": "", "trail": "", "option": "EMA25>100>200", "rec": "-"},
        {"name": "VWAP-BNC", "enabled": False, "tp": "", "sl": "", "trail": "", "option": "VWAP 근접", "rec": "-"},
        {"name": "OB-IMB", "enabled": False, "tp": "", "sl": "", "trail": "", "option": "실시간 호가 imbalance", "rec": "실전 추천 안함"},
    ]
    return render_template("strategy.html", config=config, strategies=strategies)

@app.route("/risk")
def risk():
    risk_cfg = {
        "day": 3,
        "week": 10,
        "month": 25,
        "force_pct": 5,
        "force_cnt": 3,
        "loss_stop": 5,
        "profit_stop": 8,
    }
    return render_template("risk.html", config=config, risk=risk_cfg)

@app.route("/notifications")
def notifications():
    return render_template("notifications.html")

@app.route("/funds")
def funds():
    return render_template("funds.html")

@app.route("/ai-analysis")
def ai_analysis():
    history = [
        {"time": "2025-05-18 13:00", "type": "apply", "label": "적용"},
        {"time": "2025-05-17 10:13", "type": "run", "label": "분석"},
    ]
    sample = {"count": 84, "win": 55, "profit": 1.2, "ai_result": "TP=1.8%", "ai_win": 61, "ai_profit": 1.6}
    buy_results = [dict(sample, **{"name": "M-BREAK", "key": "MBREAK"})]
    sell_results = [dict(sample, **{"name": "M-BREAK", "key": "MBREAK"})]
    return render_template(
        "ai_analysis.html",
        history=history,
        buy_results=buy_results,
        sell_results=sell_results,
    )

@app.route("/settings")
def user_settings():
    return render_template("settings.html", config=config, secrets=secrets)

@app.route("/api/start-bot", methods=["POST"])
def start_bot():
    logger.info("[API] 봇 시작 요청")
    settings["running"] = True
    return jsonify(result="success", message="봇이 시작되었습니다.")

@app.route("/api/stop-bot", methods=["POST"])
def stop_bot():
    logger.info("[API] 봇 중지 요청")
    settings["running"] = False
    return jsonify(result="success", message="봇이 정지되었습니다.")

@app.route("/api/apply-strategy", methods=["POST"])
def apply_strategy():
    # 실제 전략 설정 코드 (생략)
    data = request.json
    logger.info(f"[API] 전략 적용: {data}")
    settings["strategy"] = data.get("strategy", "M-BREAK")
    return jsonify(result="success", message="전략이 적용되었습니다.")

@app.route("/api/save-strategy", methods=["POST"])
def save_strategy():
    data = request.json
    logger.info(f"[API] 전략 저장: {data}")
    return jsonify(result="success", message="전략 설정이 저장되었습니다.")

@app.route("/api/save-risk", methods=["POST"])
def save_risk():
    data = request.json
    logger.info(f"[API] 리스크 설정 저장: {data}")
    return jsonify(result="success", message="리스크 설정이 저장되었습니다.")

@app.route("/api/save-settings", methods=["POST"])
def save_settings():
    data = request.json
    logger.info(f"[API] 사용자 설정 저장: {data}")
    return jsonify(result="success", message="설정이 저장되었습니다.")

@app.route("/api/run-analysis", methods=["POST"])
def run_analysis():
    logger.info("[API] AI 분석 실행")
    return jsonify(result="success", message="AI 분석을 실행했습니다.")

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
    app.run(debug=True)
