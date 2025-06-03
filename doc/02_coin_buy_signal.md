# 코인 매수 시그널 생성 로직

본 문서는 `01_selecting_coins_to_buy.md`에서 선정된 코인을 대상으로 매수 시그널을 어떻게 계산하는지 설명합니다.

## 역할
- F2 모듈은 최근 1분봉 데이터를 수집해 간단한 머신러닝 모델로 **매수 가능성**을 예측합니다.
- 예측 결과와 RSI/추세 조건을 결합하여 최종 매수 시그널을 결정합니다.

## 사용되는 관련 파일
| 경로 | 설명 |
| --- | --- |
| `f2_ml_buy_signal/02_ml_buy_signal.py` | 전체 파이프라인과 실시간 예측 로직을 포함합니다. |
| `f2_ml_buy_signal/01_buy_indicator.py` | EMA와 RSI 기반의 기본 필터 함수를 제공합니다. |
| `config/f5_f1_monitoring_list.json` | 매수 신호를 계산할 코인 목록입니다. |
| `config/f2_f2_realtime_buy_list.json` | 계산된 매수 신호가 저장되는 파일입니다. |
| `logs/f2/f2_ml_buy_signal.log` | 매수 신호 계산 과정의 로그가 기록됩니다. |

## 사용되는 함수
- `run_if_monitoring_list_exists()` – 모니터링 목록이 존재할 때만 `run()`을 호출합니다. 【F:f2_ml_buy_signal/02_ml_buy_signal.py†L361-L371】
- `run()` – 각 코인에 대해 `check_buy_signal()`을 호출하고 결과를 JSON 파일에 기록합니다. 【F:f2_ml_buy_signal/02_ml_buy_signal.py†L322-L359】
- `check_buy_signal()` – 모델 예측 값과 지표 조건을 확인하여 `(buy, rsi_flag, trend_flag)`를 반환합니다. 【F:f2_ml_buy_signal/02_ml_buy_signal.py†L256-L303】

## 동작 흐름
1. `signal_loop.py` 또는 외부 스케줄러가 `run_if_monitoring_list_exists()`를 호출합니다.
2. 각 코인에 대해 최근 60개의 1분봉을 다운로드하고 결측값을 처리합니다.
3. `03_feature_engineering.py` 모듈의 `add_features()`를 사용해 피처를 계산합니다.
4. 로드한 모델이 확률을 반환하면 0.5 이상 여부를 판단하여 `buy` 플래그를 만듭니다.
5. `01_buy_indicator.py`의 EMA/RSI 조건도 만족해야 최종 매수 시그널(`buy_signal`)이 1로 기록됩니다.
6. 결과는 `config/f2_f2_realtime_buy_list.json`에 저장되며 로그는 `logs/f2/f2_ml_buy_signal.log`에서 확인할 수 있습니다.

## 로그 위치 및 설명
- `logs/f2/f2_ml_buy_signal.log`에 각 단계의 성공 여부와 예측 확률이 기록됩니다.
- 예를 들어 `[CHECK] KRW-BTC prob=0.67` 형식으로 남으므로 어떤 코인이 어떤 확률로 매수 대상이 되었는지 추적할 수 있습니다.
