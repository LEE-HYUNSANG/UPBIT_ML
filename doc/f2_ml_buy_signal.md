# F2 실시간 ML 매수 신호

`f2_ml_buy_signal/f2_ml_buy_signal.py`는 머신러닝을 이용해 실시간 매수 가능성을 판단합니다.
`config/coin_list_monitoring.json` 파일이 존재할 때만 동작하며 1분봉 데이터가 갱신되는 시점에 호출됩니다.
## 주요 경로
| 파일/폴더 | 설명 |
| --- | --- |
| `f2_ml_buy_signal/f2_ml_buy_signal.py` | 전체 로직을 담은 스크립트 |
| `f2_ml_buy_signal/f2_data/` | 각 단계별 Parquet 파일 저장 위치 |
| `config/coin_list_monitoring.json` | 모니터링할 코인 목록 |
| `config/coin_realtime_buy_list.json` | 실시간 매수 후보 |
| `config/coin_realtime_sell_list.json` | 매수 시 설정되는 손절/익절 값 |
| `config/risk.json` | 기본 SL/TP 비율 등 위험 관리 파라미터 |
| `logs/f2_ml_buy_signal.log` | 실행 로그 |

## 동작 순서
1. `run_if_monitoring_list_exists()`가 `coin_list_monitoring.json` 파일 존재 여부를 확인합니다.
2. 파일이 있으면 `run()`이 실행되어 리스트의 각 심볼에 대해 다음 과정을 거칩니다.
   1. **데이터 수집** – `fetch_ohlcv()`가 최근 60개 1분봉을 다운로드합니다. 실패 시 0.2초 간격으로 세 번 재시도합니다.
   2. **정제 및 지표 계산** – `_clean_df()`와 `_add_features()`가 데이터를 정리하고 EMA, RSI 등 기본 지표를 생성합니다.
   3. **라벨 생성** – `_label()`이 미래 5분 후 가격을 기준으로 라벨을 부여합니다.
   4. **학습/예측** – `_train_predict()`가 데이터를 학습한 뒤 마지막 행에 대해 로지스틱 회귀 예측을 수행하여 확률이 0.5 이상이면 매수 대상으로 판단합니다.
   5. **리스트 갱신** – 매수 신호가 감지되면 `coin_realtime_buy_list.json`과 `coin_realtime_sell_list.json`에 해당 심볼이 기록됩니다.
      위험 파라미터는 `risk.json`에서 읽어옵니다.
3. 모든 과정은 `logs/f2_ml_buy_signal.log`에 단계별로 남아 이후 분석 시 활용됩니다.

이렇게 F2 모듈은 가벼운 로지스틱 회귀 모델을 즉석 학습하여 각 1분봉 마감 시점에 매수 여부를 판단합니다. ML 파이프라인에서 선별된 모니터링 대상만 처리하므로 빠르게 동작하며 실시간 트레이딩에 적합합니다.
