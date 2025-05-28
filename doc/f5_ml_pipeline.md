# f5_ml_pipeline 구조

이 문서는 1분봉 초단타 매매를 위한 머신러닝 파이프라인 구조를 설명합니다. 스크립트는 단계별로 분리되어 있으며 산출물은 `f5_ml_pipeline/ml_data/` 하위에 저장됩니다.

## 폴더 구성

- `01_data_collect.py` 데이터 수집
- `02_data_cleaning.py` 데이터 전처리
- `03_feature_engineering.py` 지표 계산
- `04_labeling.py` 라벨 생성
- `05_split.py` 학습/검증/테스트 분할([사용법](05_split.md))
- `06_train.py` 모델 학습([사용법](06_train.md))
- `07_eval.py` 모델 평가
- `08_predict.py` 예측 수행
- `ml_data/` 단계별 데이터 저장 폴더
- `config/train_config.yaml` 학습 설정 파일
- `utils.py` 공통 함수

## 사용 방법

필요 패키지는 `f5_ml_pipeline/requirements.txt`를 통해 설치합니다.
각 스크립트는 독립적으로 실행할 수 있으며, 설정은 `train_config.yaml`을 참고합니다.

각 단계의 상세 설명은 `doc/` 폴더의 개별 문서를 참고합니다. 특히 데이터 정제 절차는
[doc/data_cleaning.md](data_cleaning.md)에서 다룹니다. 지표 계산 방법은
[doc/feature_engineering.md](feature_engineering.md) 문서를 참고하세요.
[doc/labeling.md](labeling.md)에서 라벨 생성 규칙을 확인할 수 있습니다.
