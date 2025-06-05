# UPBIT AutoTrader HS

UPBIT AutoTrader HS 프로젝트는 트레이딩 대상 코인을 선별하고 매수/매도 신호를 계산하는 도구 모음입니다.

## 개요
이 프로젝트는 네 개의 주요 모듈로 구성됩니다:
- **F1 Universe Selector**: 거래 가능한 티커를 수집합니다.
- **F2 Signal Engine**: OHLCV 데이터를 분석하여 매수/매도 신호를 생성합니다.
- **F3 Order Executor**: 주문과 포지션을 관리합니다.
- **F4 Risk Manager**: 손실 상황을 감시하고 일시 중지 또는 중단을 수행합니다.

자세한 내용은 [문서 폴더](doc/README.md)에서 확인하세요.

## 설치 방법
소스 코드를 개발 모드로 설치하려면 다음 명령을 실행합니다.

```bash
pip install -e .
```

이 명령은 `requirements.txt`에 정의된 패키지를 함께 설치합니다. `pandas`, `scikit-learn` 등 ML 신호 스크립트에 필요한 의존성이 자동으로 포함되며 `f5_ml_pipeline/06_optuna_tpe.py` 실행에 필요한 `optuna`, `lightgbm`도 함께 설치됩니다.

## 유니버스 캐시
마지막으로 선택된 트레이딩 유니버스는 `config/current_universe.json`에 저장됩니다.
이 파일은 `f1_universe.universe_selector.update_universe()`가 작성하며, 시작 시 `load_universe_from_file()`로 불러옵니다.
외부 프로세스에서도 같은 유니버스를 사용할 수 있도록 공유됩니다.

## 주문호가 일괄 조회
`f1_universe.universe_selector.apply_filters`는 최대 100개 티커의 호가 정보를 한 번에 받아와 API 호출 수를 줄입니다.

## `signal_loop.py` 실행
F1/F2 루프를 시작하려면 다음 명령을 사용합니다.

```bash
python signal_loop.py
```

로그는 `logs/F1-F2_loop.log`에 기록되며, 용량이 100MB를 넘으면 자동으로 회전합니다. 독립적인 ML 매수 신호 루틴을 실행하려면 프로젝트 루트에서 다음과 같이 실행하세요.

```bash
python -m f2_ml_buy_signal.02_ml_buy_signal
```

결과는 `logs/f2/f2_ml_buy_signal.log`에 저장됩니다. 필요한 패키지가 없으면 이 로그 파일에 오류도 기록됩니다.
`run()` 함수는 `config/f2_f2_realtime_buy_list.json`을 갱신하며
 Flask 스케줄러가 자동으로 `buy_list_executor.execute_buy_list()`를 호출해 즉시 주문합니다.

## 주문 모듈 실행
빠른 테스트를 위해 직접 주문 모듈을 실행할 수 있습니다.

```bash
python f3_order/order_executor.py
```

또는 프로덕션 환경에서는 다음과 같이 모듈 형태로 실행하는 것을 권장합니다.

```bash
python -m f3_order.order_executor
```

두 방법 모두 기본 `OrderExecutor` 인스턴스를 시작하며 결과는 `logs/F3_order_executor.log`에 기록됩니다.

## 웹 대시보드 실행
Flask 애플리케이션을 실행하려면 다음 명령을 사용합니다.

```bash
python app.py
```

서버는 포트 3000에서 동작하며 `http://localhost:3000`으로 접속할 수 있습니다.
서버 시작 시 다음 세 가지 백그라운드 작업이 실행됩니다.
- `f5_ml_pipeline/01_data_collect.py` : 1분봉 OHLCV 데이터를 지속적으로 수집합니다.
- `f2_ml_buy_signal/02_ml_buy_signal.py` : 15초마다 실시간 매수 목록을 갱신합니다.
- `f5_ml_pipeline/run_pipeline.py` : 5분마다 모델을 재학습하고 평가합니다.

## 자격 증명 설정
프로그램을 사용하려면 Upbit API 키와 Telegram 봇 토큰이 필요합니다.
 `f3_order.utils.load_env()`는 환경 변수 또는 `.env.json` 파일에서 값을 읽습니다.
예시 파일이 리포지토리에 포함되어 있으므로, 실제 값이 담긴 `.env.json`을 Git에 올리지 않도록 주의하세요.

`.env.json` 파일 내용 예시는 다음과 같습니다.
```json
{
  "UPBIT_KEY": "<your key>",
  "UPBIT_SECRET": "<your secret>",
  "TELEGRAM_TOKEN": "<telegram token>",
  "TELEGRAM_CHAT_ID": "<chat id>"
}
```
파일은 `app.py`와 같은 위치에 두고 `.gitignore`에 추가해 관리합니다.

자격 증명 로딩 문제는 `logs/F3_utils.log`에서 확인할 수 있으며
 설정이 완료되면 주문 실행 시마다 간단한 Telegram 알림을 받습니다.
자세한 내용은 [doc/30_utilities/telegram_notifications.md](doc/30_utilities/telegram_notifications.md)
와 [doc/30_utilities/telegram_remote_control.md](doc/30_utilities/telegram_remote_control.md)를 참고하세요.

## 원격 제어
거래 루프는 매 사이클마다 `server_status.txt`를 확인합니다. 기본 위치는 `remote_control.py`와 같은 폴더이며
 파일 내용이 `ON`이면 정상 실행되고 `OFF`이면 거래를 중지합니다. Telegram `/on` `/off` 명령으로도 이 파일을 업데이트할 수 있으며
 `SERVER_STATUS_FILE` 환경 변수로 위치를 변경할 수 있습니다.

`/api/auto_trade_status` 엔드포인트는 이 파일을 실시간으로 동기화합니다. `POST` 요청으로 상태를 변경하면 즉시 `server_status.txt`가 업데이트되어 재시작 없이 반영됩니다.

## F4 위험 관리 모듈
F4 모듈은 드로우다운과 일일 손실, 실행 오류를 감시하며 상태 머신으로 동작합니다.
- **ACTIVE** : 정상 거래 허용
- **PAUSE** : 설정된 시간 동안 신규 진입 차단
- **HALT** : 모든 포지션 청산 후 수동 재시작 전까지 중단

`pause()`, `halt()`, `disable_symbol()` 호출 시 관련 포지션을 자동으로 정리하고 `ExceptionHandler.send_alert()`를 통해 Telegram 알림을 보냅니다
. 위험 이벤트는 `logs/risk_events.db`에 기록됩니다.

매수 설정 파일(`config/f6_buy_settings.json`)이 변경되면 `hot_reload()`가 즉시 감지해 새로운 파라미터를 적용하며, `OrderExecutor`도 변경된 수량 정보를 반영합니다.

중단 상태에서 복구하려면 애플리케이션을 재시작하거나 `periodic()`이 다시 `ACTIVE` 상태로 전환될 때까지 기다리면 됩니다.

## 초기 잔고 동기화
프로그램 시작 시 `PositionManager`가 Upbit API로부터 잔고를 받아 5,000원 이상 보유 중인 코인을 `imported` 포지션으로 등록합니다.
 무시된 잔고와 함께 `logs/position_init.log`에 기록되고, 요약 알림이 전송됩니다.

## REST API 엔드포인트
대시보드에서 사용하는 가벼운 REST API가 제공됩니다.

### `/api/auto_trade_status`
- `GET` : 현재 자동 거래 상태를 반환합니다.
  ```json
  {"enabled": false, "updated_at": "2024-05-27 10:12:11"}
  ```
- `POST` : `{ "enabled": true }` 형식으로 상태를 변경합니다. 서버 시작 시 기본값은 `{"enabled": false}`이며, 비활성화되어도 모니터링 루프는 계속 동작합니다.

### `/api/open_positions`
- `GET` : 주문 모듈이 관리 중인 포지션 목록을 JSON 배열로 반환합니다. 포지션이 없으면 빈 배열(`[]`)을 돌려줍니다.
  ```json
  [
    {"symbol": "KRW-BTC", "qty": 1, "status": "open"}
  ]
  ```

### `/api/events`
- `GET` : `logs/events.jsonl`에서 최근 이벤트를 반환합니다. `limit` 파라미터로 개수를 조절할 수 있습니다.

### `/api/strategies`
- `GET` : 전략 목록과 on/off 상태, 우선순위를 반환합니다.
- `POST` : 각 항목에 `short_code`, `on`, `order` 키가 포함된 목록을 저장합니다. 저장 후 즉시 설정이 반영됩니다.

## 대시보드 데이터 매핑
`templates/01_Home.html`과 `templates/02_Strategy.html`에서 새 REST API를 사용해 데이터를 갱신합니다.
 "실시간 포지션 상세" 표는 `/api/open_positions`를, "실시간 알림/이벤트" 목록은 `/api/events`를 이용하며 5초마다 새 데이터를 불러옵니다.

```javascript
function fetchPositions() {
    fetch('/api/open_positions')
        .then(r => r.json())
        .then(renderPositions);
}

function fetchEvents() {
    fetch('/api/events')
        .then(r => r.json())
        .then(renderEvents);
}

setInterval(fetchPositions, 5000);
setInterval(fetchEvents, 5000);
```

포지션 객체는 `symbol`, `strategy`, `entry_price`, `avg_price`, `current_price`,
 `eval_amount`, `pnl_percent`, `pyramid_count`, `avgdown_count` 값을 포함합니다.

 이벤트 객체는 `timestamp`와 `message`를 지니며, `strategy` 필드는 포지션을 열 때 사용한 매수 전략 이름을 기록합니다.

## FAQ 및 문제 해결
주문이 실행되지 않을 경우 [문제 해결 가이드](doc/30_utilities/troubleshooting.md)를 참고하세요.
