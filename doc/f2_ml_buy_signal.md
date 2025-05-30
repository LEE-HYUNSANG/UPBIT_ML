# F2 경량 ML 매수 신호

`f2_ml_buy_signal/f2_ml_buy_signal.py`는 실시간 매수를 위한 간소화된 머신러닝 파이프라인을 한 번에 수행합니다.
OHLCV 수집, 클리닝, 피처 생성, 라벨링, 학습, 예측을 모두 실행하며 최종으로 **매수 신호 여부**만 반환합니다.

## 주요 경로

| 경로 | 설명 |
| --- | --- |
| `config/f5_f1_monitoring_list.json` | 모니터링할 코인 목록. 목록이 없으면 스크립트가 실행되지 않습니다. |
| `logs/f2_ml_buy_signal.log` | 전체 과정의 로그가 저장되는 파일. |
| `f2_ml_buy_signal/f2_data/` | 단계별 중간 데이터가 저장되는 폴더. |

## 핵심 함수

### `run_if_monitoring_list_exists()`
`f5_f1_monitoring_list.json` 파일이 존재할 때 `run()`을 호출합니다. 없으면 로그만 남기고 종료합니다.

### `run()`
1. 파일에서 심볼 목록을 읽어 `check_buy_signal()`을 순회합니다.
2. 매수 후보가 발견되면 다음과 같은 구조의 리스트를 `config/f2_f2_realtime_buy_list.json`에 저장합니다.

   ```json
   [
       {"symbol": "KRW-BTC", "buy_signal": 1, "rsi_sel": 1, "trend_sel": 1,
        "thresh_pct": 0.003, "loss_pct": 0.003}
   ]
   ```

3. 결과와 과정을 모두 `logs/f2_ml_buy_signal.log`에 기록합니다.

### `check_buy_signal(symbol)`
1. F5 파이프라인의 `01_data_collect.py`부터 `06_train.py`까지를 순차 실행해 최신 데이터를 학습합니다.
2. `08_predict.py`로 가장 최근 1분봉의 예측 결과를 얻습니다.
3. 예측 값이 1이고 `f2_buy_indicator`의 RSI/추세 조건을 만족하면 `(True, True, True)`를 반환합니다.

## 동작 순서

1. `signal_loop.py` 혹은 상위 스케줄러가 1분봉 종료 시 `run_if_monitoring_list_exists()`를 호출합니다.
2. 스크립트는 `f5_f1_monitoring_list.json`이 존재할 때만 각 코인의 매수 신호를 판별합니다.
3. 매수 신호가 `True`로 판단되면 해당 코인이 실시간 매수 리스트에 추가되고, 매도 기준은 `f4_f2_risk_settings.json`에서 가져와 `f2_f2_realtime_sell_list.json`에 함께 기록됩니다.
4. 모든 로그와 저장 위치는 `logs/f2_ml_buy_signal.log` 파일에서 확인할 수 있습니다.

`f2_ml_buy_signal.py`를 통해 실시간으로 간단한 모델 학습과 예측을 반복하므로, 별도의 대용량 데이터 없이도 빠르게 매수 후보를 판단할 수 있습니다.
