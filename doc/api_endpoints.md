# REST API 엔드포인트

`app.py`의 Flask 서버는 웹 대시보드를 위한 간단한 REST 인터페이스를 제공합니다.
서버는 `PORT` 환경 변수(기본값 `3000`)가 지정한 포트에서 대기하며 모든 응답은
JSON으로 인코딩됩니다.

API 호출 로그는 `logs/events.jsonl`에 추가되어 대시보드에서 작업 내역을 확인할
수 있습니다.

## `/api/auto_trade_status`
- **GET** – 자동 매매 활성 여부를 반환합니다.
- **POST** – 상태를 갱신합니다. 예시 페이로드: `{ "enabled": true }`.

## `/api/open_positions`
- **GET** – 현재 열린 포지션을 나열합니다. 없으면 빈 배열을 반환합니다.

## `/api/events`
- **GET** – `logs/events.jsonl`에서 최근 로그 항목을 반환합니다. 선택적 `limit`
  쿼리 파라미터로 항목 수를 조절할 수 있습니다.

## `/api/strategies`
- **GET** – 전략 설정을 조회합니다.
- **POST** – 목록을 갱신합니다. 각 항목은 `short_code`, `on`, `order` 키를
  포함해야 합니다.

## `/api/buy_monitoring`
- **GET** – `config/f2_f2_realtime_buy_list.json` 내용을 반환합니다. 응답에는 예상
  승률과 평균 ROI(가능한 경우)가 포함되며 마지막 F5 완료 시간은 `MMDD_HHMM`
  형식으로 제공됩니다.

## API 사용 방법

아래 예시는 로컬에서 3000 포트로 실행 중인 서버를 `curl`로 제어하는 방식입니다.

```bash
# Check whether trading is active
curl http://localhost:3000/api/auto_trade_status

# Enable trading
curl -X POST -H "Content-Type: application/json" \
     -d '{"enabled": true}' \
     http://localhost:3000/api/auto_trade_status
```

모든 엔드포인트는 JSON 객체를 반환합니다. 실패한 요청은 `logs/events.jsonl`에
기록됩니다.

## 설정

API 사용을 위해 별도의 인증은 필요하지 않지만 거래 루프는 `config/` 하위의 JSON
파일을 통해 구성되어야 합니다. 주요 파일은 주문 크기와 기본 한도를 조정하는
`config/f6_buy_settings.json`입니다. 이 파일을 수정하면 다음 루프 주기부터 적용되며
결과는 `logs`에 기록됩니다.
