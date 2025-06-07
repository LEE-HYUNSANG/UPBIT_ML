# 코인 매수 시그널 생성 로직

본 문서는 `01_selecting_coins_to_buy.md`에서 선정된 코인을 대상으로 `f2_buy_signal.check_signals()` 함수가 어떻게 사용되는지 설명합니다. 이 함수는 `f5_ml_pipeline/ml_data/08_pred/{symbol}_pred.csv` 파일을 읽어 세 가지 조건을 분석한 뒤 다음과 같은 딕셔너리를 반환합니다.

```python
signals = check_signals("KRW-BTC")
# {"signal1": True, "signal2": True, "signal3": False}
```

세 값이 모두 `True`일 때만 실매수 대상으로 간주합니다.

## 역할
- F2 모듈은 F5 단계의 예측 CSV를 읽어 세 가지 조건을 평가합니다.
- 세 신호가 모두 참일 때만 실매수 대상으로 간주합니다.

## 사용되는 관련 파일
| 경로 | 설명 |
| --- | --- |
| `f2_buy_signal/01_buy_indicator.py` | EMA와 RSI 기반의 기본 필터 함수를 제공합니다. |
| `config/f5_f1_monitoring_list.json` | 매수 신호를 계산할 코인 목록입니다. |
| `config/f2_f3_realtime_buy_list.json` | 계산된 매수 신호가 저장되는 파일입니다. |
| `logs/f2/f2_buy_signal.log` | 매수 신호 계산 과정의 로그가 기록됩니다. |

## 사용되는 함수
- `check_signals(symbol)` – `08_pred` 폴더의 CSV에서 최근 행을 읽어 세 신호 값을 반환합니다.

## 동작 흐름
1. `signal_loop.py` 또는 외부 스케줄러가 예측 결과 파일을 주기적으로 확인합니다.
2. CSV 파일에서 최근 행을 읽어 세 가지 조건을 평가한 뒤 `config/f2_f3_realtime_buy_list.json`을 갱신합니다.

## 로그 위치 및 설명
- `logs/f2/f2_buy_signal.log`에 각 단계의 성공 여부와 예측 확률이 기록됩니다.
- 예를 들어 `[CHECK] KRW-BTC prob=0.67` 형식으로 남으므로 어떤 코인이 어떤 확률로 매수 대상이 되었는지 추적할 수 있습니다.
