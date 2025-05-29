# 코인 매도 모니터링 로직

이 문서는 보유 중인 코인을 언제 매도할지 판단하는 과정과 매도 주문 처리를 설명합니다. 매도 조건은 F2 모듈의 `f2_signal`과 F3 모듈의 `PositionManager`에서 관리하는 FSM(상태머신)에 의해 결정됩니다.

## 관련 파일
- `f2_signal/signal_engine.py` – 매도 조건을 계산하는 `f2_signal` 함수
- `f3_order/position_manager.py` – 포지션 상태를 갱신하고 매도 주문을 실행하는 주요 로직 포함
- `f3_order/order_executor.py` – `manage_positions` 메서드에서 `PositionManager.hold_loop` 호출

## 주요 함수와 변수

### `f2_signal`의 매도 신호
`f2_signal`에서 1분 봉 데이터를 기반으로 매도 공식을 평가합니다. 매도 조건을 충족하면 반환 딕셔너리의 `sell_signal`이 `True`가 되고 `sell_triggers`에 전략 코드가 기록됩니다.【F:f2_signal/signal_engine.py†L380-L520】

### `PositionManager.hold_loop()`
1Hz 주기로 실행되며 각 포지션의 현재 가격을 갱신하고 손익을 계산합니다. 설정된 손절(`SL_PCT`), 익절(`TP_PCT`), 트레일링 스탑(`TRAIL_*`) 조건에 따라 `execute_sell`을 호출해 포지션을 정리합니다.【F:f3_order/position_manager.py†L221-L292】【F:f3_order/position_manager.py†L312-L355】

### `PositionManager.execute_sell(position, exit_type, qty=None)`
주어진 포지션을 시장가로 매도합니다. 주문 후 남은 수량이 없으면 포지션 상태가 `closed`로 변경됩니다. 슬리피지 계산 결과는 `ExceptionHandler`로 전달됩니다.【F:f3_order/position_manager.py†L316-L337】

### 주요 설정 값
- `SL_PCT` – 손절 기준 퍼센트
- `TP_PCT` – 익절 기준 퍼센트
- `TRAILING_STOP_ENABLED` – 트레일링 스탑 사용 여부
- `TRAIL_START_PCT`, `TRAIL_STEP_PCT` – 트레일링 스탑 시작/발동 기준

이 값들은 `config/setting_date/Latest_config.json`에서 관리됩니다.【F:config/setting_date/Latest_config.json†L1-L23】

## 동작 흐름
1. `signal_loop.py`가 오픈 포지션을 가진 심볼에 대해 `f2_signal(calc_sell=True)`을 실행합니다.
2. `sell_signal`이 `True`로 돌아오면 해당 포지션의 전략 코드와 매칭하여 `PositionManager.execute_sell`이 호출됩니다.
3. 동시에 `hold_loop`는 매초 포지션의 손익률을 계산해 손절, 익절, 트레일링 스탑 조건을 점검하고 필요 시 자동 매도합니다.

이렇게 매도 로직은 신호 기반 매도와 포지션 상태 기반 매도로 구성되어 있어 다양한 상황에서 손실을 최소화하고 이익을 확정할 수 있습니다.
