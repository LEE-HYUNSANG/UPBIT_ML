# 프로젝트 개요

이 문서는 현재 저장소의 주요 모듈과 동작 흐름을 한국어로 간단히 정리합니다. 
자동 매매 로직을 추가하기 전에 구조를 빠르게 파악할 수 있도록 작성되었습니다.

## 주요 구성
- **app.py**: Flask 서버 및 REST API, SocketIO 이벤트를 정의합니다. 
  5분마다 업비트 시세를 갱신하고 매수/매도 모니터링 데이터를 계산합니다.
- **bot/**: 실제 매매 로직을 담당하는 패키지입니다.
  - `trader.py` – 업비트 주문을 실행하는 메인 클래스
  - `strategy.py` – 22가지 매매 전략 함수와 `select_strategy` 헬퍼
  - `indicators.py` – EMA, RSI 등 기술적 지표 계산
  - `ai_analysis.py` – AI 기반 파라미터 추천 예시
  - `runtime_settings.py` – 실행 중 변경되는 설정 저장소
- **templates/**: Jinja2 HTML 템플릿. 대시보드와 각 설정 페이지가 포함됩니다.
- **static/**: 공용 JavaScript, CSS 파일.
- **config/**: 사용자 설정과 시크릿 키, 모니터링 코인 목록 저장 경로.

## 실행 흐름
1. `utils.load_secrets()` 로 API 키를 읽어 오류 여부를 확인합니다.
2. `app.py` 초기화 과정에서 시장 데이터를 불러오고 백그라운드 스레드를 시작합니다.
3. `/api/start-bot` 호출 시 `UpbitTrader` 가 별도 스레드에서 `run_loop` 를 돌며
   전략을 평가하고 주문을 실행합니다.
4. 대시보드는 SocketIO 를 통해 실시간 알림과 잔고, 매수 신호를 갱신합니다.

추가 기능 구현 시 이 문서를 참고해 모듈 위치와 호출 순서를 파악하면 됩니다.
