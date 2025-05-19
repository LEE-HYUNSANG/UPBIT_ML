# UPBIT AutoTrading Example

This repository contains a minimal Flask + SocketIO demo for an automated trading dashboard. The application renders Bootstrap templates with Jinja variables so pages display data from the server.

## Structure
- **app.py** – Flask application providing HTML pages and API routes. SocketIO is used to push live notifications.
- **templates/** – Jinja2 templates extending `base.html`. Each page receives values such as `positions`, `strategies` and `alerts` from Flask.
- **static/js/main.js** – Common JavaScript handling API calls, SocketIO events and draggable layout.
- **static/css/custom.css** – Consolidated styles for all pages.

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

## Running
Install requirements and start the server:
```bash
pip install -r requirements.txt
python app.py
```
The app runs with `socketio.run` so WebSocket notifications work by default.

## Windows 설치 가이드
Windows 10/11 + Visual Studio C++ 빌드툴 환경에서 다음 순서로 준비합니다.

1. [Python 3.11](https://www.python.org/) 설치 시 "Add python to PATH" 를 선택합니다.
2. [Visual Studio Build Tools](https://visualstudio.microsoft.com/visual-cpp-build-tools/) 을 설치해 C++ 컴파일 도구를 준비합니다.
3. 저장소를 클론한 후 `cmd` 또는 PowerShell 에서 아래 명령을 실행합니다.

```cmd
pip install --upgrade pip
pip install -r requirements.txt
```

`talib-binary` 패키지를 사용하므로 별도 빌드 오류 없이 설치됩니다.

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
