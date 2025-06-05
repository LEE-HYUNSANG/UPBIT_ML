# 설정 파일 개요

이 문서는 `config/` 디렉터리에 있는 모든 JSON 파일을 설명합니다. 파일 이름은
어떤 모듈이 파일을 생성하고 소비하는지를 나타내는 `[from]_[to]_[name].json`
형식을 따릅니다. 프로젝트가 익숙하지 않은 기획자도 이해할 수 있도록 서술했습니다.


## f5_f1_monitoring_list.json
**F5** 머신러닝 파이프라인이 선정한 코인 목록입니다. 각 항목은 `symbol`,
`thresh_pct`, `loss_pct`를 포함합니다. **F1**과 **F2** 모듈은 이 파일을 로드하여
실시간으로 모니터링할 코인을 파악합니다. `app.py`가 시작될 때마다 이 파일은
초기화됩니다.

## f1_f5_data_collection_list.json
ML 학습을 위해 수집할 코인 목록입니다. **F1** 모듈이 관리하며 **F5** 데이터 수집기가
읽습니다.


## f1_f3_coin_positions.json
현재 보유 중인 포지션을 나타냅니다. 계정 잔고를 가져올 때 **F1**이 최초로 생성하며
이후에는 **F3** 주문 실행기가 계속 갱신합니다.

## f2_f2_realtime_buy_list.json
코인이 ML과 지표 조건을 만족할 때 **F2**가 생성하는 딕셔너리 목록입니다. 각 항목은
`symbol`, `buy_signal`, `rsi_sel`, `trend_sel`, `buy_count`, `pending`을 포함합니다.
`buy_signal`이 1이고 `buy_count`가 0인 경우에만 신규 주문 대상으로 간주합니다.
매수가 체결되면 `buy_count`가 1로 변경되며 이후 실행에서도 유지되어 중복 등록을
막습니다. `pending` 플래그는 해당 종목에 대한 주문이 처리 중인지 나타냅니다.
`app.py`가 시작될 때마다 이 파일은 초기화됩니다.

## f3_f3_realtime_sell_list.json
현재 보유 중인 종목의 목록만 포함합니다. 매수 주문이 체결되면 종목이 추가되고 포지션이
종료되면 제거됩니다. ML 매수 목록은 여기에 존재하는 종목에 대해 `buy_count`를 1로
유지합니다. 시작 시 계좌 잔고를 기반으로 이 파일이 다시 생성됩니다.

## f4_f2_risk_settings.json
이 파일은 삭제되었습니다. 과거에는 손절률이나 트레일링 스톱 설정 같은 구식 위험
매개변수를 저장했습니다.

## f3_f3_pending_symbols.json
이 파일은 삭제되었습니다. 주문 대기 상태는 이제 `f2_f2_realtime_buy_list.json`의
`pending` 플래그에 직접 기록됩니다.

## f3_f3_order_config.json
이 파일은 삭제되었습니다. `config_path`가 `None`이거나 경로가 없을 경우
`OrderExecutor`는 파일 로드를 건너뜁니다. 재시도 횟수와 기본 수량은 코드에서 직접
제공됩니다.

## f6_buy_settings.json
웹 UI로 제어되는 매수 주문 설정입니다. `STARTUP_HOLD_SEC`, `ENTRY_SIZE_INITIAL`,
`MAX_SYMBOLS`, `LIMIT_WAIT_SEC_1`, `1st_Bid_Price`, `LIMIT_WAIT_SEC_2`,
`2nd_Bid_Price`, `FALLBACK_MARKET` 값을 저장합니다. 기본값은 각각 `300`, `7000`,
`7`, `30`, `"BID1"`, `20`, `"BID1+"`, `false`입니다. `STARTUP_HOLD_SEC`가 0보다 크면
`app.py` 실행 후 처음 N초 동안 새 매수를 하지 않습니다. 이 값들은 주문 실행기의 기본
설정을 덮어쓰며 위험 관리자에도 반영됩니다. `FALLBACK_MARKET`가 활성화되면 첫
번째 지정가 주문이 실패하고 두 번째 시도가 없을 때 시장가 주문을 보냅니다.

## f6_sell_settings.json
열린 포지션을 어떻게 청산할지 제어합니다. 주요 항목은 다음과 같습니다.

* `TP_PCT` – 초기 익절 주문을 넣을 진입가 대비 비율
* `MINIMUM_TICKS` – TP 가격 계산 시 유지해야 할 최소 틱 간격. 반올림한 TP가 진입가와
  이 간격 이내라면 간격을 유지하도록 상향 조정합니다.
* `TS_FLAG` – `'ON'`이면 트레일링 스톱 로직을 활성화하고 `'OFF'`이면 비활성화합니다.
* `HOLD_SECS` – 포지션이 이 시간 이상 유지된 후에야 트레일링 스톱이 활성화됩니다.
* `TRAIL_START_PCT` – 트레일링 스톱 모니터링을 시작하기 전에 도달해야 하는 수익률
  기준
* `TRAIL_STEP_PCT` – 트레일링 스톱이 활성화된 후 허용되는 최고가 대비 하락폭

기본값은 각각 `0.18`, `2`, `'OFF'`, `180`, `0.3`, `1.0`입니다.

`OrderExecutor`는 시작 시 이 설정을 로드하여 보관합니다. 트레일링 스톱 플래그는
`PositionManager`에서 사용할 `TRAILING_STOP_ENABLED`로 변환됩니다.
## f5_f5_strategy_params.json
ML 파이프라인에서 사용하는 각 전략의 기본 하이퍼파라미터입니다.


