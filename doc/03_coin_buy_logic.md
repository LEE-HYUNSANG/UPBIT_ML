# 매수 주문 처리 로직

이 문서는 F2 모듈이 생성한 매수 시그널을 바탕으로 실제 주문이 어떻게 체결되는지를 설명합니다.

## 역할
- `OrderExecutor`와 `PositionManager`가 협력하여 주문 체결, 포지션 등록, 추후 관리까지 담당합니다.
- 슬리피지나 주문 실패 같은 예외 상황은 `ExceptionHandler`가 처리합니다.

## 사용되는 관련 파일
| 경로 | 설명 |
| --- | --- |
| `f3_order/order_executor.py` | 매수 신호를 받아 주문을 실행하는 핵심 클래스입니다. |
| `f3_order/smart_buy.py` | IOC 주문과 시장가 주문을 조합해 체결률을 높이는 함수입니다. |
| `f3_order/position_manager.py` | 포지션을 저장하고 손익을 계산하며 매도 조건을 감시합니다. |
| `config/f2_f2_realtime_buy_list.json` | 매수 시그널과 체결 여부(`buy_count`)가 기록됩니다. |
| `config/f3_f3_realtime_sell_list.json` | 매도 시 세부 설정(TP/SL)을 저장하는 파일입니다. |
| `logs/F3_order_executor.log` | 주문 실행 과정과 각 신호 처리 내역이 기록됩니다. |
| `logs/F3_smart_buy.log` | 실매수 로직의 상세 로그입니다. |
| `logs/F3_position_manager.log` | 포지션 상태 변화가 기록됩니다. |

## 사용되는 함수
- `OrderExecutor.entry()` – 매수 신호를 받아 `smart_buy()`를 호출하고 포지션을 등록합니다. 【F:f3_order/order_executor.py†L122-L162】
- `smart_buy()` – IOC 주문 실패 시 시장가로 재시도하며 주문 결과를 반환합니다. 【F:f3_order/smart_buy.py†L22-L59】
- `PositionManager.open_position()` – 체결된 주문 정보를 내부 리스트와 파일에 저장합니다. 【F:f3_order/position_manager.py†L87-L117】
- `PositionManager.refresh_positions()` – 계좌 잔고와 시세를 조회하여 포지션 정보를 업데이트합니다. 【F:f3_order/position_manager.py†L173-L228】

## 동작 흐름
1. `signal_loop.py`가 `f2_signal()` 결과를 받아 `OrderExecutor.entry()`에 전달합니다.
2. `entry()` 함수는 이미 보유 중이거나 리스크 매니저가 차단한 코인은 건너뜁니다.
3. `smart_buy()`가 IOC 주문을 시도하고 필요하면 시장가 주문으로 전환합니다. 체결 여부는 `filled` 필드로 확인합니다.
4. 주문이 성공하면 `PositionManager.open_position()`이 호출되어 포지션이 등록되고 실시간 매도 설정 리스트가 갱신됩니다.
5. `refresh_positions()`와 `hold_loop()`가 매초 실행되어 현재가, 손익률, 손절/익절 조건을 지속적으로 계산합니다.

## 로그 위치 및 설명
- `logs/F3_order_executor.log`에서 주문 시도와 결과뿐 아니라 신호를 받은 시점과 "매수 없음" 판단까지 모두 확인할 수 있습니다.
- `logs/F3_smart_buy.log`에는 IOC/시장가 주문 전환 기록이 남아 슬리피지 상황을 파악할 수 있습니다.
- `logs/F3_position_manager.log`에는 포지션 오픈과 종료, 손익 변화가 시간 순서대로 저장됩니다.
