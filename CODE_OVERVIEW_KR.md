# 코드 구조 요약 (한글)

본 프로젝트는 Flask 웹 대시보드와 업비트 자동매매 예제 코드로 구성되어 있습니다. 각 파일의 용도는 다음과 같습니다.

## 최상위 파일
- **app.py**: Flask 애플리케이션과 API 라우트 정의. SocketIO 실시간 알림 사용. 실시간 시세는 1분마다 Upbit API에서 갱신해 필터 조건에 따라 대시보드에 표시합니다.
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

## config 디렉터리
- **config/config.json**: 예제 설정 값.
- **config/secrets.json**: API 키 등 비밀 정보 예시.

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

이 문서는 비개발자도 빠르게 전체 구조를 파악할 수 있도록 작성되었습니다.
