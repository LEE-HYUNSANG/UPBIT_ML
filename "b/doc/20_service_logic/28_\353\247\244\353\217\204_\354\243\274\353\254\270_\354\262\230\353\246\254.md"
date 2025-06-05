# 매도 주문 처리 로직

파일명은 buy_signal이지만 내용은 매도 주문 처리 절차를 정리합니다.

## 역할
- `PositionManager.execute_sell()`가 실제 매도 주문을 전송하고 포지션을 갱신합니다.
- 매도가 완료되면 주문 정보가 데이터베이스와 JSON 파일에 기록되어 이후 통계나 리스크 관리에 활용됩니다.

## 사용되는 관련 파일
| 경로 | 설명 |
| --- | --- |
| `f3_order/position_manager.py` | 매도 주문 실행과 포지션 업데이트 로직이 포함됩니다. |
| `f3_order/order_executor.py` | `manage_positions()` 루프에서 매도 조건을 주기적으로 확인합니다. |
| `logs/F3_position_manager.log` | 매도 주문 체결 내역이 기록됩니다. |
| `logs/orders.db` | 모든 주문 정보가 SQLite 형식으로 저장됩니다. |

## 사용되는 함수
- `PositionManager.execute_sell(position, exit_type, qty=None)` – 지정된 수량을 시장가로 매도하고 포지션 상태를 업데이트합니다. 【F:f3_order/position_manager.py†L438-L488】
- `OrderExecutor.manage_positions()` – 1초 주기로 포지션 상태를 갱신하고 필요 시 `execute_sell()`을 호출합니다. 【F:f3_order/order_executor.py†L164-L176】

## 동작 흐름
1. `signal_loop.py`에서 `executor.manage_positions()`가 호출되어 모든 포지션을 점검합니다.
2. `PositionManager.hold_loop()`가 손익률을 계산해 익절 또는 손절 조건을 만족하면 `execute_sell()`을 호출합니다.
3. `execute_sell()`은 `place_order()`를 통해 시장가 매도 주문을 전송하고,
   주문이 체결되면 포지션을 `closed` 상태로 변경하고 알림을 전송합니다.
4. 주문 결과는 `orders.db`와 `f1_f3_coin_positions.json`에 저장되어 다음 실행 시에도 기록이 유지됩니다.

## 로그 위치 및 설명
- 매도 주문과 관련된 모든 로그는 `logs/F3_position_manager.log`에 남습니다.
- 데이터베이스 파일 `logs/orders.db`를 통해 과거 주문 내역을 상세히 조회할 수 있습니다.
