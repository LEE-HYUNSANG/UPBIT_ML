# 리스크 관리 로직

이 문서는 F4 모듈이 계좌 손익과 시스템 상태를 감시해 자동으로 매매를 제어하는 과정을 설명합니다.
`RiskManager`는 모든 포지션을 통제하며 필요에 따라 PAUSE나 HALT 상태를 결정합니다.

## 관련 파일
- `f4_riskManager/risk_manager.py` – 리스크 FSM과 핵심 로직을 포함한 `RiskManager`
- `f4_riskManager/risk_config.py` – 설정 파일을 읽어들이는 `RiskConfig`
- `f4_riskManager/risk_logger.py` – 상태 변화 및 이벤트를 DB와 로그 파일에 기록
- `f4_riskManager/risk_utils.py` – 공용 유틸과 상태 정의

로그 파일은 `logs/F4_risk_manager.log`와 `logs/risk_fsm.log`에 저장됩니다.

## 주요 함수와 변수

### `RiskManager.update_account(account_pnl, mdd, monthly_mdd, open_symbols)`
현재 계좌 손익과 보유 코인 목록을 업데이트합니다. 여기서 전달된 정보는 다음 `check_risk` 호출 때 사용됩니다.【F:f4_riskManager/risk_manager.py†L60-L71】

### `RiskManager.check_risk()`
1Hz 주기로 호출되어 손실 한도와 MDD 한도, 동시 보유 코인 수를 점검합니다.
조건을 위반하면 `pause()` 또는 `halt()`가 실행됩니다. [f4_riskManager/risk_manager.py]

### `RiskManager.pause(minutes, reason="")`
일정 시간 동안 신규 진입을 차단합니다. 기존 포지션은 모두 청산하며 상태가 `PAUSE`로 바뀝니다.【F:f4_riskManager/risk_manager.py†L120-L139】

### `RiskManager.halt(reason="")`
심각한 손실이나 장애가 발생했을 때 모든 포지션을 청산하고 상태를 `HALT`로 전환합니다. 이후 매매가 중지됩니다.【F:f4_riskManager/risk_manager.py†L148-L167】

### `RiskManager.hot_reload()`

설정 파일(`Latest_config.json`) 변경을 감지해 실시간으로 파라미터를 갱신합니다.
갱신 시 `OrderExecutor`의 거래 금액 등도 함께 업데이트됩니다.
### `RiskManager.on_slippage(symbol)`
슬리피지 한도를 초과한 주문이 발생하면 횟수를 기록하고 일정 횟수 이상이면 `disable_symbol`을 호출합니다.【F:f4_riskManager/risk_manager.py†L77-L87】

### `RiskManager.disable_symbol(symbol)`
특정 심볼의 신규 진입을 막고 보유 포지션을 강제 청산합니다.【F:f4_riskManager/risk_manager.py†L125-L136】

### `RiskManager.periodic()`
1초 주기로 호출되어 일시정지 해제, 설정 파일 변경 감지 및 `check_risk` 실행을 처리합니다.【F:f4_riskManager/risk_manager.py†L169-L180】


### 주요 설정 값
`config/setting_date/Latest_config.json` 파일에서 다음과 같은 리스크 파라미터를 관리합니다.
- `DAILY_LOSS_LIM` – 하루 누적 손실 한도(%)
- `MDD_LIM` – 최근 30일 최대 낙폭 한도(%)
- `MONTHLY_MDD_LIM` – 월간 최대 낙폭 한도(%)
- `MAX_SYMBOLS` – 동시에 보유 가능한 코인 수 제한
- `SLIP_MAX` – 허용 슬리피지 한도(%)

이 외에도 `ENTRY_SIZE_INITIAL`, `AVG_SIZE`, `PYR_SIZE` 등의 주문 크기 설정도 같은 파일에서 조정합니다.

## 동작 흐름
1. `signal_loop.py`에서 매 루프마다 `RiskManager.update_account`로 실현 손익과 보유 코인을 전달합니다.
2. `RiskManager.periodic()`이 호출되어 설정 파일 변경 여부를 체크하고 `check_risk`를 실행합니다.
3. 손실 한도 초과 또는 슬리피지 이벤트가 발생하면 `pause` 또는 `disable_symbol`을 통해 신규 진입을 막고 필요 시 포지션을 강제 청산합니다.
4. 치명적인 손실이 발생하거나 MDD 한도가 초과되면 `halt`가 호출되어 모든 매매가 중단됩니다.
5. 상태 전이는 `risk_fsm.log`에 기록되며 주요 이벤트는 `RiskLogger`를 통해 로그 파일과 Telegram 알림으로 전송됩니다.

`RiskManager`를 통해 시스템은 예상치 못한 손실을 빠르게 제한하고 안정적으로 운용될 수 있습니다.
