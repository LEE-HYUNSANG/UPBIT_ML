# 매수 주문 처리 로직

이 문서는 F2 모듈이 생성한 매수 시그널을 바탕으로 실제 주문이 어떻게 체결되는지를 설명합니다.

## 역할
- `OrderExecutor`와 `PositionManager`가 협력하여 주문 체결, 포지션 등록, 추후 관리까지 담당합니다.
- 슬리피지나 주문 실패 같은 예외 상황은 `ExceptionHandler`가 처리합니다.

## 사용되는 관련 파일
| 경로 | 설명 |
| --- | --- |
| `f3_order/order_executor.py` | 매수 신호를 받아 주문을 실행하는 핵심 클래스입니다. |
| `f3_order/smart_buy.py` | 지정가 주문을 한 번 시도하고 50초 동안 대기합니다. |
| `f3_order/position_manager.py` | 포지션을 저장하고 손익을 계산하며 매도 조건을 감시합니다. |
| `config/f2_f2_realtime_buy_list.json` | 매수 시그널과 체결 여부(`buy_count`)가 기록됩니다. |
| `config/f3_f3_realtime_sell_list.json` | 매도 시 세부 설정(TP/SL)을 저장하는 파일입니다. |
| `logs/F3_order_executor.log` | 주문 실행 과정과 각 신호 처리 내역이 기록됩니다. |
| `logs/F3_smart_buy.log` | 실매수 로직의 상세 로그입니다. |
| `logs/F3_position_manager.log` | 포지션 상태 변화가 기록됩니다. |

## 사용되는 함수
- `OrderExecutor.entry()` – 매수 신호를 받아 `smart_buy()`를 호출하고 포지션을 등록합니다. 【F:f3_order/order_executor.py†L122-L162】
- `smart_buy()` – 지정가 주문을 50초간 대기하며 한 번만 시도합니다. 【F:f3_order/smart_buy.py†L25-L62】
- `PositionManager.open_position()` – 체결된 주문 정보를 내부 리스트와 파일에 저장합니다. 【F:f3_order/position_manager.py†L87-L117】
- `PositionManager.refresh_positions()` – 계좌 잔고와 시세를 조회하여 포지션 정보를 업데이트합니다. 【F:f3_order/position_manager.py†L173-L228】

## 동작 흐름
1. `signal_loop.py`가 `f2_signal()` 결과를 받아 `OrderExecutor.entry()`에 전달합니다.
2. `entry()` 함수는 이미 보유 중이거나 리스크 매니저가 차단한 코인은 건너뜁니다.
   동시에 동일 코인 주문이 진행 중이면 `pending_symbols` 집합에 기록되어
   추가 주문을 무시합니다.
3. `smart_buy()`가 지정가 주문을 보내 50초 동안 체결을 기다립니다. 체결되지 않으면 주문을 취소하고 포기합니다.
   이때 손절과 익절 기준은 **최초 시도한 가격**을 사용하며 두 번째 시도에서 더 높은 가격에 체결되더라도 계산 값은 바뀌지 않습니다.
4. 주문이 성공하면 `PositionManager.open_position()`이 호출되어 포지션이 등록되고 실시간 매도 설정 리스트가 갱신됩니다.
   체결되지 않아 주문을 취소하면 `buy_count`가 0으로 초기화되어 다음 시도에서 다시 매수가 가능합니다.
   일부만 체결된 경우에는 `pending` 상태로 남겨 추가 체결을 기다립니다.
   이후 포지션이 매도로 정리되면 `buy_count`도 0으로 돌아갑니다.
5. `refresh_positions()`와 `hold_loop()`가 매초 실행되어 현재가, 손익률, 손절/익절 조건을 지속적으로 계산합니다.

## 로그 위치 및 설명
- `logs/F3_order_executor.log`에서 주문 시도와 결과뿐 아니라 신호를 받은 시점과 "매수 없음" 판단까지 모두 확인할 수 있습니다.
- `logs/F3_smart_buy.log`에는 두 차례 지정가 주문 시도와 취소 과정이 기록됩니다.
- `logs/F3_position_manager.log`에는 포지션 오픈과 종료, 손익 변화가 시간 순서대로 저장됩니다.

## 실행 방법

개발 중 `order_executor.py`를 직접 실행하면 패키지를 인식하지 못해
`ImportError: attempted relative import with no known parent package` 오류가 발생하곤 했습니다.
현재는 스크립트 내부에서 경로를 보정해 두었으므로 다음과 같이 실행해도 됩니다.

```bash
python f3_order/order_executor.py
```

하지만 실제 운영 환경에서는 모듈 형태로 호출하는 편이 안정적입니다.

```bash
python -m f3_order.order_executor
```
