# 코드 구조 요약 (한글)

본 프로젝트는 Flask 웹 대시보드와 업비트 자동매매 예제 코드로 구성되어 있습니다. 각 파일의 용도는 다음과 같습니다.

## 최상위 파일
 - **app.py**: Flask 애플리케이션과 API 라우트 정의. SocketIO 실시간 알림 사용.
   업비트 원화 마켓 데이터를 1분마다 갱신해 가격/거래대금 순으로 정렬한 뒤
   대시보드 필터 조건에 맞는 코인만 모니터링과 매매에 사용합니다.
- **Dockerfile**: 컨테이너 환경 설정 예시.
- **requirements.txt**: 필요한 파이썬 패키지 목록.
- **scripts/run_gunicorn.sh**: gunicorn으로 앱 실행 스크립트.
- **README.md**: 프로젝트 설명(영문).

## bot 패키지
- **bot/__init__.py**: 패키지 초기화용 빈 파일.
- **bot/ai_analysis.py**: AI 전략 파라미터 추천 모듈.
- **bot/indicators.py**: EMA, RSI 등 기술적 지표 계산 함수.
- **bot/strategy.py**: 9가지 매매 전략 함수와 선택 로직.
- **bot/trader.py**: 업비트 API를 활용한 메인 트레이더 클래스.
- **app.py/load_market_signals**: 1분마다 업비트 시세와 거래량을 불러와 필터링에 사용.

## config 디렉터리
 - **config/config.json**: 예제 설정 값.
 - **config/secrets.json**: API 키 등 비밀 정보 예시.
 - **config/market.json**: 업비트 연결 실패 시 사용할 시세 예시 데이터.

## templates 디렉터리 (Jinja2 HTML)
- **base.html**: 기본 레이아웃.
- **index.html**: 메인 대시보드.
- **strategy.html**: 전략 설정 페이지.
- **risk.html**: 리스크 관리 페이지.
- **funds.html**: 자금 설정 페이지.
- **notifications.html**: 알림 목록.
- **settings.html**: API 키 등 설정.
- **ai_analysis.html**: AI 분석 결과 페이지.

## static 디렉터리
- **static/js/main.js**: 공통 자바스크립트 (API 호출, 드래그 레이아웃 등).
- **static/css/custom.css**: 전체 스타일 시트.

앱은 1분마다 업비트에서 모든 원화마켓 코인의 가격과 거래금액을 불러와 거래대금 순으로 정렬합니다. 대시보드에서 설정한 가격대와 순위 조건은 이 실시간 데이터에 적용되어 모니터링과 자동매매 대상이 결정됩니다.

이 문서는 비개발자도 빠르게 전체 구조를 파악할 수 있도록 작성되었습니다.
