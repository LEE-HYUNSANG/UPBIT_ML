# 코인 매도 시그널 생성 로직

보유한 포지션을 언제 청산할지는 매수와 달리 여러 모듈이 협업하여 결정합니다. 기본적인 익절/손절 조건은 F3 모듈에서 계산하고, 위험 관리 차원에서는 F4 모듈이 개입합니다.

## 역할
- `PositionManager`는 실시간 가격 변동을 추적하며 손익률이 기준을 넘으면 매도 시그널을 발생시킵니다.
- `RiskManager`는 계좌 손실 한도나 MDD를 초과할 경우 강제로 매도하도록 지시합니다.

## 사용되는 관련 파일
| 경로 | 설명 |
| --- | --- |
| `f3_order/position_manager.py` | 보유 포지션의 손익률을 계산하고 익절/손절 조건을 감시합니다. |
| `f4_riskManager/risk_manager.py` | 계좌 단위 손실 한도 초과 시 모든 포지션을 청산합니다. |
| `config/f3_f3_realtime_sell_list.json` | 현재 보유 중인 심볼 목록을 저장하는 파일입니다. |
| `logs/F3_position_manager.log` | 매도 조건 충족 여부와 실행 내역이 기록됩니다. |
| `logs/F4_risk_manager.log` | 위험 관리 이벤트가 저장됩니다. |

## 사용되는 함수
- `PositionManager.hold_loop()` – 각 포지션의 현재가를 조회하여 TP/SL, 보유 시간 등을 검사합니다. 【F:f3_order/position_manager.py†L230-L271】
- `PositionManager.execute_sell()` – 매도 주문을 실행하고 포지션 정보를 갱신합니다. 【F:f3_order/position_manager.py†L336-L359】
- `RiskManager.check_risk()` – 일 손실, MDD, 동시 보유 코인 수 등을 점검해 필요 시 `pause()`나 `halt()`를 호출합니다. 【F:f4_riskManager/risk_manager.py†L89-L118】

## 동작 흐름
1. `signal_loop.py`의 메인 루프에서 `PositionManager.hold_loop()`가 매초 실행됩니다.
2. 각 포지션의 손익률을 계산해 익절(TP) 또는 손절(SL) 기준을 충족하면 `execute_sell()`로 시장가 주문을 보냅니다.
3. `RiskManager`가 계좌 손실 한도를 초과했다고 판단하면 `pause()` 또는 `halt()`가 호출되어 모든 포지션을 강제 정리합니다.
4. 매도 시그널이 발생하거나 포지션 상태가 변경될 때마다 관련 로그가 각 파일에 남습니다.

## 로그 위치 및 설명
- `logs/F3_position_manager.log`에서 "Position exit" 메시지를 통해 어떤 사유로 매도가 이루어졌는지 확인할 수 있습니다.
- 위험 관리로 인한 강제 청산은 `logs/F4_risk_manager.log`와 `logs/risk_fsm.log`에 기록되어 추후 분석이 가능합니다.
