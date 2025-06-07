# F2 매수 신호 모듈

`f2_buy_signal/02_ml_buy_signal.py`는 실시간 매수를 위한 경량 머신러닝 파이프라인입니다.
업비트 1분봉 데이터를 읽어 F5 파이프라인에서 학습된 모델을 이용해 **매수 신호 여부**만 빠르게 판단합니다.

## 주요 경로

| 경로 | 설명 |
| --- | --- |
| `config/f5_f1_monitoring_list.json` | 모니터링할 코인 목록. 목록이 없으면 스크립트가 실행되지 않습니다. |
| `logs/f2/f2_ml_buy_signal.log` | 전체 과정의 로그가 저장되는 파일. |
| `f2_buy_signal/f2_data/` | 단계별 중간 데이터가 저장되는 임시 폴더. 실행이 끝나면 자동으로 삭제됩니다. |

## 핵심 함수

### `run_if_monitoring_list_exists()`
`f5_f1_monitoring_list.json` 파일이 존재할 때 `run()`을 호출합니다. 없으면 로그만 남기고 종료합니다.

### `run()`
1. 파일에서 심볼 목록을 읽어 `check_buy_signal()`을 순회합니다.
2. 모니터링하는 각 코인에 대해 다음과 같은 구조의 리스트를
   `config/f2_f2_realtime_buy_list.json`에 저장합니다.

   ```json
   [
       {"symbol": "KRW-BTC", "buy_signal": 1, "rsi_sel": 1, "trend_sel": 1,
        "buy_count": 0}
   ]
   ```

    모든 코인의 상태가 매 실행마다 덮어쓰기 되며,
    이미 매수가 완료되어 `buy_count`가 1인 코인은 해당 값을 그대로 유지하여
    `buy_signal` 값이 `1`이고 `buy_count`가 `0`인 항목만이 실제 매수 후보가 됩니다.
3. 결과와 과정을 모두 `logs/f2/f2_ml_buy_signal.log`에 기록합니다.

### `check_buy_signal(symbol)`
1. F5 파이프라인에서 미리 학습된 모델을 불러옵니다.
2. 업비트에서 최근 1분봉 데이터를 가져와 `03_feature_engineering.py`의 `add_features()`로 피처를 계산합니다.
3. 모델이 반환한 확률이 0.5 이상이고 `01_buy_indicator`의 RSI/추세 조건을 만족하면 `(True, True, True)`를 반환합니다.

## 동작 순서

1. `f5_ml_pipeline`의 예측 결과가 갱신되면 `run_if_monitoring_list_exists()`가 자동으로 호출됩니다.
2. 스크립트는 `f5_f1_monitoring_list.json`이 존재할 때만 각 코인의 매수 신호를 판별합니다.
3. 매수 신호가 `True`로 판단되면 해당 코인이 실시간 매수 리스트에만 기록됩니다.
   실제 주문이 체결된 뒤에야 별도의 로직이 매도 설정 리스트(`f3_f3_realtime_sell_list.json`)
   를 갱신합니다.
4. 모든 로그와 저장 위치는 `logs/f2/f2_ml_buy_signal.log` 파일에서 확인할 수 있습니다.

`02_ml_buy_signal.py`는 학습된 모델을 활용해 최신 데이터를 즉시 예측하므로, 별도의 대용량 데이터 없이도 빠르게 매수 후보를 판별할 수 있습니다.

## 실행 방법

레포지터리 루트에서 모듈 형태로 실행하면 import 오류 없이 동작합니다.

```bash
python -m f2_buy_signal.02_ml_buy_signal
```
