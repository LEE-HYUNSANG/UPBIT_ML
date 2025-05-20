# AGENTS Instructions

These guidelines apply to all files in this repository.

- When modifying Python code, run `pytest` before committing.
- Keep line lengths under 120 characters.
- Use clear and descriptive commit messages summarizing the changes.

## Logic Overview (for 개발자/기획자/실무자)
- `app.py` : Flask 웹 서버와 API 라우트 정의, SocketIO 알림 처리
- `bot/trader.py` : 업비트 자동매매 스레드, 주문 실행 로직
- `bot/strategy.py` : 9가지 매매 전략 함수와 선택 로직
- `bot/indicators.py` : EMA, RSI 등 기술적 지표 계산
- `bot/ai_analysis.py` : AI 파라미터 추천 예시
- `bot/runtime_settings.py` : 런타임 설정을 dataclass 로 관리

