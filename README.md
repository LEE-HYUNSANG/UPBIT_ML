# UPBIT AutoTrading Example

This repository contains a minimal Flask + SocketIO demo for an automated trading dashboard.  All HTML templates use Jinja2 variables so tables and forms are filled with server side data.

## Structure
- **app.py** – Flask application providing HTML pages and API routes. SocketIO is used to push live notifications.
- **templates/** – Jinja2 templates extending `base.html`. Pages include `index.html`, `strategy.html`, `risk.html`, `funds.html`, `notifications.html`, `settings.html` and `ai_analysis.html`.
  Each template gets variables like `positions`, `strategies`, `alerts` or `settings` directly from Flask.
- **static/js/main.js** – Common JavaScript handling API calls, SocketIO events, draggable layout and real time table updates.
- **static/css/custom.css** – Consolidated styles for all pages with no inline styles left in templates.

## Example variables passed to templates
```python
return render_template(
    "index.html",
    running=settings["running"],
    positions=positions,
    alerts=alerts,
    signals=signals,
)
```

## API usage
Buttons with a `data-api` attribute automatically send the nearest form data via `fetch`:
```html
<button data-api="/api/start-bot">봇 시작</button>
```
The JavaScript in `main.js` will call `/api/start-bot` and show any returned message via a modal.
SocketIO events `notification`, `positions` and `alerts` push real time updates to the browser.

## Running
Install requirements and start the server:
```bash
pip install wheel
pip install -r requirements.txt
python app.py
```
The app runs with `socketio.run` so WebSocket notifications work by default.
Real time events are pushed to the browser via SocketIO and displayed with `showAlert()` in `main.js`.

## Windows 설치 가이드
Windows 10/11 + Visual Studio C++ 빌드툴 환경에서 다음 순서로 준비합니다.

1. [Python 3.11](https://www.python.org/) 설치 시 "Add python to PATH" 를 선택합니다.
2. [Visual Studio Build Tools](https://visualstudio.microsoft.com/visual-cpp-build-tools/) 을 설치해 C++ 컴파일 도구를 준비합니다.
3. 저장소를 클론한 후 `cmd` 또는 PowerShell 에서 아래 명령을 실행합니다.

```cmd
pip install --upgrade pip
pip install wheel
pip install -r requirements.txt
```

`talib-binary` 패키지를 포함하고 있어 일반적으로 빌드 오류 없이 설치됩니다.
만약 설치 도중 `numpy` 혹은 `talib` 관련 컴파일 오류가 발생한다면
Visual Studio C++ 빌드 툴이 제대로 설치됐는지 확인하고 다음 명령으로
설치 도구를 최신화합니다.

```cmd
python -m pip install --upgrade setuptools wheel
pip install --no-binary :all: ta-lib
```

서버는 아래와 같이 실행합니다.

```cmd
python app.py
```

웹 브라우저에서 `http://localhost:5000` 접속 후 대시보드를 확인합니다.

## 운영 예시 (Gunicorn & Docker)

Gunicorn + eventlet 로 배포할 수 있습니다.

```bash
./scripts/run_gunicorn.sh
```

도커 사용 시:

```bash
docker build -t upbit-bot .
docker run -p 8000:8000 upbit-bot
```

`scripts/run_gunicorn.sh` 는 간단한 운영 자동화 스크립트 예시입니다.
