# F2 매수 신호 모듈

`f2_buy_signal` 패키지는 F5 단계에서 생성된 예측 파일을 읽어 세 가지 간단한 조건을 확인합니다. `check_signals(symbol)` 함수는 `{symbol}_pred.csv`의 마지막 행을 분석해 `signal1`, `signal2`, `signal3` 값을 반환합니다.

## 주요 경로

| 경로 | 설명 |
| --- | --- |
| `f5_ml_pipeline/ml_data/08_pred/` | F5 모델의 예측 CSV가 저장되는 위치 |
| `logs/f2/f2_buy_signal.log` | 신호 계산 중 남는 로그 파일 |

## 동작 방식
1. `check_signals()`는 예측 CSV에서 `buy_signal`(또는 `buy_prob`) 값을 읽어 `signal1`을 결정합니다.
2. 같은 행의 `rsi14` 값이 40~60 사이면 `signal2`가 `True`가 됩니다.
3. `ema5`가 `ema20`보다 크면 `signal3`을 `True`로 설정합니다.
4. 반환된 세 값이 모두 `True`일 때 매수 조건을 만족한 것으로 간주합니다.

예측 파일이 없거나 읽을 수 없으면 세 신호 모두 `False`를 반환합니다.
