# F5ML_09_backtest.py 사용법

`08_predict.py` 결과와 `04_label`에서 추출한 가격 데이터를 사용해
매수 신호(`buy_signal==1`)가 발생하면 포지션을 잡고 TP/SL/TS 중 하나가
충족될 때까지 무한 보유하는 방식의 백테스트를 수행합니다.

## 입력 파일
- `f5_ml_pipeline/ml_data/08_pred/{symbol}_pred.csv`
- `f5_ml_pipeline/ml_data/04_label/{symbol}_label.parquet`
- `f5_ml_pipeline/ml_data/04_label/{symbol}_best_params.json`

## 주요 기능
- 트레일링 스탑을 포함한 TP/SL/TS 규칙 중 가장 먼저 충족되는 조건에서 즉시 청산합니다.
- 왕복 0.1% 수수료를 반영한 순수익률과 총수익률을 모두 기록합니다.
- 승률, 손실률, Sharpe Ratio, 최대 낙폭(MDD) 등을 계산해 JSON 요약으로 저장합니다.
- 각 트레이드는 CSV 파일로 기록합니다.

## 출력
- `f5_ml_pipeline/ml_data/09_backtest/{symbol}_trades.csv`
- `f5_ml_pipeline/ml_data/09_backtest/{symbol}_summary.json`

## 실행 방법
```bash
python f5_ml_pipeline/09_backtest.py
```
모든 스크립트는 자신의 폴더 기준으로 절대 경로를 사용하기 때문에 어디서 실행해도 `f5_ml_pipeline/ml_data/` 하위에 백테스트 결과가 저장됩니다.
