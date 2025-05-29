# F5ML_06_train.py 사용법

`ml_data/05_split/`에 저장된 학습/검증 데이터를 읽어
LightGBM 분류 모델을 학습하고 `ml_data/06_models/`에 저장합니다.

## 주요 기능
- EMA, RSI, ATR 등 주요 지표를 피처로 사용합니다.
- 라벨 1을 매수 신호로 간주하여 이진 분류 모델을 학습합니다.
- 검증 데이터로 정확도, F1 점수, AUC 등을 계산하여 `*_metrics.json`에 기록합니다.

## 실행 방법
```bash
python f5_ml_pipeline/06_train.py
```

모델 학습 파라미터는 `f5_ml_pipeline/config/train_config.yaml`에서 관리합니다.
`n_estimators`와 `early_stopping_rounds` 등 값을 수정해 실험할 수 있으며
코드에는 하이퍼파라미터를 직접 입력하지 않습니다.
