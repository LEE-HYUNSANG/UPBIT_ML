# REST API 엔드포인트

`app.py`의 Flask 서버는 웹 대시보드에서 사용하는 간단한 REST API를 제공합니다.
서버 포트는 `PORT` 환경 변수를 따르며 기본값은 `3000`입니다. 모든 응답은 JSON 형식으로
반환됩니다. API 호출 내역은 `logs/events.jsonl`에 저장됩니다.

## `/api/auto_trade_status`
- **GET** – 자동매매 활성화 여부를 반환합니다.
- **POST** – `{ "enabled": true }` 형식으로 상태를 변경합니다.

## `/api/open_positions`
- **GET** – 현재 보유 중인 포지션 목록을 반환합니다. 없으면 빈 배열을 돌려줍니다.

## `/api/events`
- **GET** – `logs/events.jsonl`에서 최근 로그를 조회합니다. `limit` 파라미터로 개수를
  조절할 수 있습니다.

## `/api/strategies`
- **GET** – 현재 전략 설정을 가져옵니다.
- **POST** – `short_code`, `on`, `order` 필드를 포함한 목록으로 갱신합니다.

## `/api/buy_monitoring`
- **GET** – `config/f2_f3_realtime_buy_list.json`의 내용을 돌려줍니다. 예상 승률과 ROI,
  마지막 F5 완료 시각이 함께 포함됩니다.

### 사용 예시

다음 명령은 로컬에서 3000번 포트로 실행 중인 서버와 통신하는 예입니다.

```bash
# 자동매매 상태 확인
curl http://localhost:3000/api/auto_trade_status

# 자동매매 활성화
curl -X POST -H "Content-Type: application/json" \
     -d '{"enabled": true}' \
     http://localhost:3000/api/auto_trade_status
```

API 자체는 인증을 요구하지 않지만 거래 루프 설정은 `config/` 하위 JSON 파일로 관리됩니다.
주요 파일은 `config/f6_buy_settings.json`이며 수정 사항은 다음 루프에서 적용됩니다.
