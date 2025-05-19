"""
UPBIT 5분봉 자동매매 Flask 메인 앱 (초보자 상세 주석)
"""
from flask import Flask, render_template, jsonify, request, send_file
import os, shutil, logging

app = Flask(__name__)

# 로그 설정
logging.basicConfig(
    filename='logs/bot_debug.log', level=logging.DEBUG,
    format='[%(levelname)s][%(asctime)s] %(message)s'
)
logger = logging.getLogger("bot")

# 전역 변수 (설정 예시)
settings = {"running": False, "strategy": "M-BREAK", "TP": 0.02, "SL": 0.01, "funds": 1000000}

@app.route("/")
def dashboard():
    return render_template("index.html")

@app.route("/strategy")
def strategy():
    return render_template("strategy.html")

@app.route("/risk")
def risk():
    return render_template("risk.html")

@app.route("/notifications")
def notifications():
    return render_template("notifications.html")

@app.route("/funds")
def funds():
    return render_template("funds.html")

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
