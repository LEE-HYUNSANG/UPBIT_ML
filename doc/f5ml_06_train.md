# F5ML_06_train.py 사용법

`f5_ml_pipeline/ml_data/05_split/`에 저장된 학습/검증 데이터를 읽어
LightGBM 분류 모델을 학습하고 `f5_ml_pipeline/ml_data/06_models/`에 저장합니다.
모델 학습 시 사용되는 피처 목록은 데이터에 존재하는 모든 컬럼에서
`timestamp`와 `label`을 제외한 값으로 자동 결정됩니다.

## 주요 기능
- EMA, RSI, ATR 등 주요 지표를 피처로 사용합니다.
- 라벨 1을 매수 신호로 간주하여 이진 분류 모델을 학습합니다.
- 검증 데이터로 정확도, F1 점수, AUC 등을 계산하여 `*_metrics.json`에 기록합니다.
- 학습 로직은 `train_and_eval()` 함수에 구현되어 있으며, 각 심볼별 모델과 지표는 `logs/ml_train.log`에 요약됩니다.

## 실행 방법
```bash
python f5_ml_pipeline/06_train.py
```

모델과 로그 파일 위치는 스크립트 기준으로 결정되므로, 어디서 실행하더라도
`f5_ml_pipeline/ml_data/05_split/`에서 학습 데이터를 읽고 `f5_ml_pipeline/ml_data/06_models/`에 결과를 저장합
니다.

모델 학습 파라미터는 `f5_ml_pipeline/config/train_config.yaml`에서 관리합니다.
외부 패키지 없이 간단한 YAML 파서를 내장해 의존성을 최소화했으며
`n_estimators`와 `early_stopping_rounds` 값 등을 바꿔 자유롭게 실험할 수 있습니다.

학습 데이터가 한 종류의 라벨만 포함하거나 사용 가능한 피처가 없는 경우에는
경고 메시지를 남기고 해당 심볼의 학습을 건너뜁니다.

## Troubleshooting

모델 학습 중 `No further splits with positive gain` 경고가 나타날 수 있습니다. 이는
피처에 예측력이 부족하거나 라벨 분포가 지나치게 한쪽으로 치우친 경우 발생합니다.
이런 상황에서는 성능 향상이 어렵기 때문에 `train_config.yaml`의
`early_stopping_rounds` 설정에 따라 개선이 없으면 조기에 학습이 종료됩니다.
