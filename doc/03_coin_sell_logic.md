# 코인 매도 로직

이 문서는 보유 중인 코인을 언제 정리할지 결정하는 과정을 설명합니다.
매도 신호는 F2 모듈에서 계산하고, 실제 주문과 포지션 관리는
F3 모듈과 F4 리스크 매니저가 담당합니다.

## 관련 파일

| 경로 | 설명 |
| --- | --- |
| `f2_ml_buy_signal/03_buy_signal_engine/signal_engine.py` | `f2_signal()` 함수가 매도 공식을 평가합니다. |
| `f3_order/position_manager.py` | 포지션 정보를 저장하고 `hold_loop()`에서 손익을 주기적으로 계산합니다. |
| `f3_order/order_executor.py` | `manage_positions()` 메서드로 포지션 상태를 점검하고 필요 시 매도를 실행합니다. |
| `f4_riskManager/risk_manager.py` | 손실 한도 초과 시 `pause()`나 `halt()`를 통해 강제 청산을 수행합니다. |
| `config/f6_buy_settings.json` | 진입 금액과 동시 보유 코인 수 등을 지정하는 설정 파일입니다. |

로그는 `logs/F3_position_manager.log`와 `logs/F4_risk_manager.log` 등에 기록됩니다.

## 주요 함수

### `f2_signal(..., calc_sell=True)`
1분 봉 데이터를 기반으로 매도 조건을 계산합니다.
조건을 충족하면 반환 값의 `sell_signal`이 `True`가 되며
`sell_triggers`에 사용된 전략 코드가 남습니다.

### `PositionManager.hold_loop()`
초당 실행되며 각 포지션의 현재가를 가져와 손익률을 계산합니다.
손절(`SL_PCT`)과 익절(`TP_PCT`) 기준을 만족하면
`execute_sell()`을 호출합니다.

### `PositionManager.execute_sell(position, exit_type, qty=None)`
지정된 포지션을 시장가로 매도합니다.
모두 청산되면 상태가 `closed`로 바뀌고 결과가 `f1_f3_coin_positions.json`에 저장됩니다.
매도가 완료되면 `f2_f2_realtime_buy_list.json`에 해당 코인이 존재할 경우 `buy_count`가 0으로 초기화되어 다시 매수를 시도할 수 있습니다.

### `RiskManager.check_risk()`
계좌 손실이나 MDD 한도가 넘으면 `pause()` 또는 `halt()`로 진입을 차단하고
기존 포지션을 청산합니다.

## 동작 흐름

1. `signal_loop.py`는 보유 중인 각 코인에 대해 `f2_signal(calc_sell=True)`을 호출합니다.
2. `sell_signal`이 `True`이면 `PositionManager.execute_sell()`이 실행되어 시장가 주문을 보냅니다.
3. 매수 주문이 체결되면 `OrderExecutor`가 `config/f3_f3_realtime_sell_list.json`에
   해당 코인의 익절(`TP_PCT`)과 손절(`SL_PCT`) 값을 기록합니다.
4. `PositionManager`는 포지션 오픈 직후 익절가에 지정가 매도 주문을 넣습니다.
5. `hold_loop()`는 매초 손익을 계산합니다. 손절 기준을 만족하면 미리 넣어둔
   익절 지정가 주문을 취소한 뒤 시장가로 청산합니다. 익절 기준 충족 시에는
   선 주문이 체결되어 별도 조치가 필요 없습니다. 익절에 도달하지 않았을 때
   현재가가 평균 매수가 이상이면 TP 주문을 유지하고, 평균 매수가보다 낮으면
   TP 주문을 취소한 채 손절 조건만 모니터링합니다.
   포지션이 완전히 정리되면 `f3_f3_realtime_sell_list.json`에서도 해당 심볼이
   제거됩니다.
   
   2025-06 업데이트로 손익 계산이 다시 **퍼센트 단위**로 변경되었습니다.
   최신 버전에서는 틱 기반 보정을 제거하여 설정한 손절/익절 값을 그대로 사용합니다.
6. 리스크 매니저가 손실 한도 초과를 감지하면 모든 포지션을 강제 정리하고
   상태를 `PAUSE` 또는 `HALT`로 변경합니다.

이렇게 신호 기반 매도와 위험 관리 로직이 결합되어
예상치 못한 손실을 최소화하고 이익 실현을 돕습니다.
