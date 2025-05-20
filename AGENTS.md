# AGENTS Guide

본 문서는 개발자와 기획자, 실무자를 위한 내부 로직 안내서입니다. 저장소의 파이썬 코드는 모두 한글 주석을 사용하여 초보자도 쉽게 이해할 수 있도록 작성되었습니다.

- 파이썬 코드를 수정한 뒤에는 반드시 `pytest` 를 실행하여 테스트해 주세요.
- 모든 라인 길이는 120자를 넘지 않도록 유지합니다.
- 커밋 메시지는 변경 사항을 명확하게 서술합니다.

## 코드 구조 개요
### 최상위 파일
- **app.py**: Flask 서버와 API 라우트 정의. SocketIO 로 실시간 알림을 전송하며 1분 주기로 업비트 원화 마켓 데이터를 갱신합니다.
- **Dockerfile**, **requirements.txt**: 실행 환경 예시와 의존 패키지 목록.
- **scripts/run_gunicorn.sh**: Gunicorn 실행 스크립트.
- **utils.py**: 로그 설정, 텔레그램 전송, 체결강도(TIS) 계산 등 공통 함수 모음.

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

서버는 매 분마다 시세와 거래량을 받아 정렬한 뒤, 필터 조건에 맞는 코인만 `monitor_list.json` 으로 저장합니다. 이 문서는 초보자가 프로젝트 구조를 빠르게 이해할 수 있도록 작성되었습니다.
