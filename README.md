# UPBIT AutoTrading Example

This repository contains a minimal Flask + SocketIO demo for an automated trading dashboard.  All HTML templates use Jinja2 variables so tables and forms are filled with server side data.

## Structure
- **app.py** – Flask application providing HTML pages and API routes. SocketIO is used to push live notifications.
- **templates/** – Jinja2 templates extending `base.html`. Pages include `index.html`, `strategy.html`, `risk.html`, `funds.html`, `notifications.html`, `settings.html` and `ai_analysis.html`.
  Each template gets variables like `positions`, `strategies`, `alerts` or `settings` directly from Flask.
- **static/js/main.js** – Common JavaScript handling API calls, SocketIO events, draggable layout and real time table updates.
- **static/css/custom.css** – Consolidated styles for all pages with no inline styles left in templates.
- **config/market.json** – Sample market data loaded for monitoring filters.

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

## Market data
`app.py` retrieves current prices and 24h volume from Upbit once per minute. The
coins are filtered by the values in `config/filter.json` (`min_price`,
`max_price`, `rank`), and this filtered list controls both monitoring and real
trading targets.

## Running
Install requirements and start the server:
```bash
pip install wheel
pip install -r requirements.txt
python app.py
```
The app runs with `socketio.run` so WebSocket notifications work by default.
Real time events are pushed to the browser via SocketIO and displayed with `showAlert()` in `main.js`.
Market data for the monitoring table is refreshed every minute using the official Upbit API and filtered by the dashboard settings.

Every minute the server downloads the full list of KRW markets from Upbit using
`pyupbit`. Each coin's current price and 24h volume are retrieved to calculate
its volume rank. The dashboard filter (`min_price`, `max_price`, `rank`) is
applied to this list, and the resulting tickers are used for both monitoring and
trading.


## Running tests
Install `pytest` and execute the suite:
```bash
pip install pytest
pytest
```

## Secrets configuration
All API keys and tokens are read from `config/secrets.json`. Create the file before starting the server:

```json
{
  "UPBIT_KEY": "YOUR-UPBIT-KEY",
  "UPBIT_SECRET": "YOUR-UPBIT-SECRET",
  "TELEGRAM_TOKEN": "BOT-TOKEN",
  "TELEGRAM_CHAT_ID": "123456789"
}
```

`utils.load_secrets()` reads this file when the app starts. If the file is missing,
unreadable or any required value is empty the application prints an error,
logs it and exits immediately. When Telegram credentials are available (in the
file or via `TELEGRAM_TOKEN` and `TELEGRAM_CHAT_ID` environment variables) the
same message is also sent there.
Example error:
```
[ERROR] Missing required secrets: UPBIT_KEY, UPBIT_SECRET
```

`config/market.json` stores fallback market data when live fetching from Upbit
fails. Tests load this file to avoid network access.

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

`requirements.txt` 는 Windows 환경에서는 `TA-Lib`(미리 컴파일된 whl), 그
외 환경에서는 `talib-binary` 가 자동 선택되도록 환경 마커를 사용합니다.
따라서 별도 빌드 과정 없이 설치가 완료됩니다. 만약 TA-Lib 설치가 실패
한다면 [공식 배포 페이지](https://www.lfd.uci.edu/~gohlke/pythonlibs/#ta-lib)
에서 파이썬 버전에 맞는 whl 파일을 받아 직접 설치할 수 있습니다.

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
