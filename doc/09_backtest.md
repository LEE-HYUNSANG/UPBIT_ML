# 09_backtest.py 사용법

`08_predict.py`에서 생성된 `{symbol}_pred.csv`와 `04_label`의 라벨 데이터를 이용해
매수 신호(`buy_signal==1`) 발생 시점만 진입하는 간단한 백테스트를 수행합니다.

## 입력 파일
- `ml_data/08_pred/{symbol}_pred.csv`
- `ml_data/04_label/{symbol}_label.parquet`
- `ml_data/04_label/{symbol}_best_params.json`

## 주요 기능
- 진입 시점의 종가를 기준으로 라벨별 예상 청산가를 계산해 수익률을 산출합니다.
- 왕복 0.1% 수수료를 반영한 순수익률과 총수익률을 모두 기록합니다.
- 승률, 손실률, Sharpe Ratio, 최대 낙폭(MDD) 등을 계산해 JSON 요약으로 저장합니다.
- 각 트레이드는 CSV 파일로 기록합니다.

## 출력
- `ml_data/09_backtest/{symbol}_trades.csv`
- `ml_data/09_backtest/{symbol}_summary.json`

## 실행 방법
```bash
python f5_ml_pipeline/09_backtest.py
```
