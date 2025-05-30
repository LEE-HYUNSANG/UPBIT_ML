# F5ML_머신러닝 파이프라인

이 문서는 1분봉 초단타 매매 모델을 학습하기 위한 **F5ML 파이프라인**의 전체 흐름을 요약합니다. 각 단계는 독립 실행이 가능하며 결과는 `f5_ml_pipeline/ml_data/` 하위 폴더에 순차적으로 저장됩니다.

모든 파이프라인 스크립트는 자신의 위치를 `PIPELINE_ROOT` 상수로 정의하여
실행 위치와 관계없이 동일한 경로 구조를 사용합니다. 데이터와 로그 역시
이 기본 경로를 기준으로 저장됩니다.

## 단계별 스크립트

1. `00_Before_Coin.py` 코인 필터링 및 원시 데이터 수집 → `f5_ml_pipeline/ml_data/00_back_raw/`
2. `01_data_collect.py` OHLCV 다운로드 → `f5_ml_pipeline/ml_data/01_raw/`
3. `02_data_cleaning.py` 데이터 정제 → `f5_ml_pipeline/ml_data/02_clean/`
4. `03_feature_engineering.py` 지표 계산 → `f5_ml_pipeline/ml_data/03_feature/`
5. `04_labeling.py` 라벨 생성 → `f5_ml_pipeline/ml_data/04_label/`
6. `05_split.py` 학습·검증·테스트 분할 → `f5_ml_pipeline/ml_data/05_split/`
7. `06_train.py` 모델 학습 → `f5_ml_pipeline/ml_data/06_models/`
8. `07_eval.py` 모델 평가 → `f5_ml_pipeline/ml_data/07_eval/`
9. `08_predict.py` 예측 수행 → `f5_ml_pipeline/ml_data/08_pred/`
10. `09_backtest.py` 백테스트 → `f5_ml_pipeline/ml_data/09_backtest/`
11. `10_select_best_strategies.py` 전략 선별 → `f5_ml_pipeline/ml_data/10_selected/`

로그는 `f5_ml_pipeline/ml_data/09_logs/`에 `mllog_<YYYYMMDDHHMMSS>.log` 형식으로 기록되며, 1MB를 초과하면 자동으로 새 파일로 교체됩니다.

## 사용 방법

필요 패키지는 `f5_ml_pipeline/requirements.txt`에서 설치합니다. 각 스크립트는 다음과 같이 실행할 수 있습니다.

```bash
python f5_ml_pipeline/<스크립트명>.py
```

설정 값은 `f5_ml_pipeline/config/train_config.yaml`에서 관리합니다.
모든 하이퍼파라미터는 이 파일을 수정해 변경하며, 코드에는 값을 직접 적지 않습니다.
세부 동작은 `doc/` 폴더의 각 문서를 참고해 주세요.

### \uc77c\uac80 \uc2e4\ud589

04\ub2e8\uacc4 \uc774\ud6c4 \ubb38\uc11c \uc2e4\ud589\uc744 \uc21c\ucc28\uc801\uc73c\ub85c \uc218\ud589\ud558\ub824\uba74 `run_pipeline.py` \uc2a4\ud06c\ub9bd\ud2b8\ub97c \uc0ac\uc6a9\ud569\ub2c8\ub2e4. `03_feature_engineering.py` \uae4c\uc9c0 \uc644\ub8cc\ub41c \uc0c1\ud0dc\uc5d0\uc11c \uc544\ub798 \uba85\ub839\uc744 \uc2e4\ud589\ud558\uba74 `04_labeling.py`\ubd80\ud130 `10_select_best_strategies.py`\uae4c\uc9c0 \uc790\ub3d9\uc73c\ub85c \ucc98\ub9ac\ub429\ub2c8\ub2e4.

```bash
python f5_ml_pipeline/run_pipeline.py
```
모든 스크립트는 자신의 디렉터리 기준으로 절대 경로를 계산하여 실행 위치에 상관없이 `f5_ml_pipeline/ml_data/` 하위 폴더에 데이터를 저장합니다.
