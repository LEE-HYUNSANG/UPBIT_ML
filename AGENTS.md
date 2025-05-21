# AGENTS Guide

본 문서는 개발자와 기획자, 실무자를 위한 내부 로직 안내서입니다. 저장소의 파이썬 코드는 모두 한글 주석을 사용하여 초보자도 쉽게 이해할 수 있도록 작성되었습니다.

- 파이썬 코드를 수정한 뒤에는 반드시 `pytest` 를 실행하여 테스트해 주세요.
- 모든 라인 길이는 120자를 넘지 않도록 유지합니다.
- 커밋 메시지는 변경 사항을 명확하게 서술합니다.

## 코드 구조 개요
### 최상위 파일
- **app.py**: Flask 서버와 API 라우트 정의. SocketIO 로 실시간 알림을 전송하며 5분봉 마감 시점에 업비트 원화 마켓 데이터를 갱신합니다.
- **Dockerfile**, **requirements.txt**: 실행 환경 예시와 의존 패키지 목록.
- **scripts/run_gunicorn.sh**: Gunicorn 실행 스크립트.
- **utils.py**: 로그 설정, 텔레그램 전송, 체결강도(TIS) 계산 등 공통 함수 모음.
- **calc_buy_signal()**: DEBUG 레벨에서 각 지표 값을 `debug.log` 에 기록해
  전략 계산 과정을 역추적할 수 있다.

### bot 패키지
- **trader.py**: 업비트 자동매매 메인 클래스. 전략 평가 후 주문을 실행합니다.
- **strategy.py**: 아홉 가지 전략 함수와 `select_strategy` 로직.
- **indicators.py**: EMA, RSI, ATR 등 기술적 지표 계산 함수.
- **ai_analysis.py**: AI 기반 파라미터 추천 예시.
- **runtime_settings.py**: 실행 중 변경되는 설정을 dataclass 로 관리합니다.

### 기타 디렉터리
- **config/**: 봇 설정 값과 시크릿 키 예시.
- **templates/**: Jinja2 기반 HTML 대시보드 템플릿.
- **static/**: 공통 JavaScript 와 CSS 파일.

서버는 5분봉 마감마다 시세와 거래량을 받아 정렬한 뒤, 필터 조건에 맞는 코인만 `monitor_list.json` 으로 저장합니다. 이 문서는 초보자가 프로젝트 구조를 빠르게 이해할 수 있도록 작성되었습니다.

모니터링 값이 계산되면 서버에서 `refresh_data` SocketIO 이벤트를 세 번(1초 간격) 발생시켜
브라우저가 잔고와 매수 모니터링 정보를 다시 조회합니다. `/api/status` 가 반환하는
`next_refresh` 값은 다음 5분봉 마감 시각이며, 페이지의 "데이터 갱신 잔여시간" 표시가 이 값을
기준으로 갱신됩니다.
calc_buy_signal_retry() 는 각 코인을 최대 세 번 계산한다. 세 번 모두 값이 없으면 해당 행은 '⛔'과 "데이터 대기"로 남는다.
이러한 항목은 다음 5분봉 마감 10초 전까지 10초 간격으로 계속 재계산하며 값이 채워지면 즉시 `refresh_data` 이벤트로 브라우저에 반영한다.

## 개발 서버 로그
Flask 개발 서버를 사용하면 모든 HTTP 요청이 다음과 같은 형식으로 기록됩니다.
```
127.0.0.1 - - [21/May/2025 10:50:29] "GET /api/status HTTP/1.1" 200 236 0.002
```
각 항목은 IP 주소, 요청 경로, 상태 코드, 응답 크기(byte), 처리 시간을 의미합니다.
대시보드에서 `/api/status` 를 5초마다 호출하므로 개발 중에는 위와 같은 로그가 반복됩니다.

## 최근 문제 로그
다음은 CSS 인라인 스타일에서 발생한 경고 예시입니다. `templates/index.html` 의 134번째 줄에서 발견되었습니다.

```json
[
  {
    "resource": "/c:/Users/twtko/Desktop/UPBIT_AutoTrader_HS/templates/index.html",
    "owner": "_generated_diagnostic_collection_name_#0",
    "code": "css-identifierexpected",
    "severity": 8,
    "message": "식별자 필요",
    "source": "css",
    "startLineNumber": 134,
    "startColumn": 53,
    "endLineNumber": 134,
    "endColumn": 54
  }
]

[
  {
    "resource": "/c:/Users/twtko/Desktop/UPBIT_AutoTrader_HS/templates/index.html",
    "owner": "_generated_diagnostic_collection_name_#0",
    "code": "css-rcurlyexpected",
    "severity": 8,
    "message": "} 필요",
    "source": "css",
    "startLineNumber": 134,
    "startColumn": 54,
    "endLineNumber": 134,
    "endColumn": 55
  }
]

[
  {
    "resource": "/c:/Users/twtko/Desktop/UPBIT_AutoTrader_HS/templates/index.html",
    "owner": "_generated_diagnostic_collection_name_#0",
    "code": "css-ruleorselectorexpected",
    "severity": 8,
    "message": "at-rule 또는 선택기가 필요함",
    "source": "css",
    "startLineNumber": 134,
    "startColumn": 68,
    "endLineNumber": 134,
    "endColumn": 69
  }
]

[
  {
    "resource": "/c:/Users/twtko/Desktop/UPBIT_AutoTrader_HS/templates/index.html",
    "owner": "_generated_diagnostic_collection_name_#0",
    "code": "emptyRules",
    "severity": 4,
    "message": "빈 규칙 집합을 사용하지 마세요.",
    "source": "css",
    "startLineNumber": 134,
    "startColumn": 48,
    "endLineNumber": 134,
    "endColumn": 53
  }
]
```

세미콜론을 추가하여 `<span class="pin" style="left: {{ p.pin_pct }}%;"></span>` 형태로 수정하면 경고가 사라집니다.
