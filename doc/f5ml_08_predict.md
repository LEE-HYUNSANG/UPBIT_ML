# F5ML_08_predict.py 사용법

`ml_data/06_models/`에 저장된 학습된 모델을 이용해 새로운 피처 데이터에 대한 매수 신호를 예측합니다.
예측 결과는 `ml_data/08_pred/` 폴더에 `{symbol}_pred.csv` 형식으로 저장됩니다.

예측에 사용되는 피처 목록은 모델 파일에 저장된 값을 우선 사용하며,
없을 경우 입력 데이터의 모든 컬럼에서 `timestamp`를 제외한 값으로 자동 결정됩니다.

각 파일에는 다음 컬럼이 포함됩니다.

- `timestamp`
- `close`
- `buy_signal` (1이면 매수 진입)
- `buy_prob` (매수 확률 0~1)
- 주요 피처: `ema5`, `ema20`, `rsi14`, `atr14`, `vol_ratio`, `stoch_k`

## 실행 방법
```bash
python f5_ml_pipeline/08_predict.py
```
