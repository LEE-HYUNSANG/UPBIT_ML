# 코인 매수 로직

이 문서는 F2 모듈에서 매수 신호를 계산하고 F3 모듈이 실제 주문을
어떻게 수행하는지 설명합니다. 초보 기획자를 위해 관련 파일과
함수를 한눈에 볼 수 있게 정리했습니다.

## 관련 파일

| 경로 | 용도 |
| --- | --- |
| `f2_ml_buy_signal/f2_ml_buy_signal.py` | 경량 머신러닝으로 실시간 매수 신호를 판단합니다. |
| `f2_ml_buy_signal/f2_data/` | 단계별 임시 Parquet 파일 저장 위치 |
| `f2_signal/signal_engine.py` | `f2_signal()` 함수에서 1분 봉 데이터를 받아 ML 모델을 호출합니다. |
| `f3_order/order_executor.py` | 매수 신호를 받아 주문을 실행하는 `OrderExecutor` 클래스가 있습니다. |
| `f3_order/position_manager.py` | 포지션을 저장·관리하며 주문 결과를 기록합니다. |
| `config/f5_f1_monitoring_list.json` | 모니터링할 코인 목록(`symbol`, `thresh_pct`, `loss_pct`). F5 단계에서 생성됩니다. |
| `config/f2_f2_realtime_buy_list.json` | 매수 대상이 발견되면 `{심볼: 0}` 형식으로 기록됩니다. |
| `config/f2_f2_realtime_sell_list.json` | 손절·익절·트레일링 스탑 설정을 저장합니다. |
| `config/f4_f2_risk_settings.json` | 매매 금액과 손절 비율 등 위험 관리 값. |

로그는 `logs/f2_ml_buy_signal.log`, `logs/F2_signal_engine.log`,
`logs/F3_order_executor.log` 등에 남습니다.

## 주요 함수

### `run_if_monitoring_list_exists()`
`config/f5_f1_monitoring_list.json` 파일이 존재할 때만 `run()`을 호출합니다.
파일이 없으면 아무 작업도 하지 않습니다.

### `run()`
1. 모니터링 목록을 읽어 각 코인에 대해 `check_buy_signal()`을 수행합니다.
2. 신호가 `True`이면 `f2_f2_realtime_buy_list.json`과
   `f2_f2_realtime_sell_list.json`을 갱신합니다.
3. 과정과 결과는 `logs/f2_ml_buy_signal.log`에 기록됩니다.

### `f2_signal(df_1m, df_5m, symbol="", ...)`
`signal_loop.py`에서 호출되어 실제 매매 루프를 돌 때 사용됩니다.
`check_buy_signal_df()`를 이용해 1분 봉 데이터에서 바로 신호를 계산하며
매수 가능 여부를 `buy_signal` 필드로 반환합니다.

### `OrderExecutor.entry(signal)`
매수 신호가 `True`일 때 호출되어 실거래를 시도합니다.
수량 계산, 슬리피지 체크, 포지션 등록 등을 모두 처리하며
실패 시 재시도나 오류 로그가 남습니다.

## 동작 흐름

1. **전략 선별** – `f5_ml_pipeline/10_select_best_strategies.py`가
   우수 전략을 추려 `f5_f1_monitoring_list.json`을 갱신합니다.
2. **모니터링** – `signal_loop.py`에서 주기적으로 `f2_signal`을 호출해
   각 코인의 1분 봉 데이터를 분석합니다.
3. **ML 신호 판단** – `run_if_monitoring_list_exists()`가 실행되면
   별도의 경량 ML 모델이 최근 데이터를 학습한 뒤 바로 예측을 수행합니다.
   확률이 0.5 이상이면 매수 대상으로 판단합니다.
4. **주문 실행** – `OrderExecutor.entry()`가 `smart_buy()`를 호출해
   시장가 혹은 IOC 주문을 보내고, 체결되면 `PositionManager`에
   포지션이 저장됩니다.
5. **로그 기록** – 모든 과정은 `logs` 폴더에 남아 나중에 분석할 수 있습니다.

위 절차를 통해 시스템은 모니터링 목록에 있는 코인을 실시간으로 살펴보고
매수 조건이 충족되면 자동으로 주문을 진행합니다.
