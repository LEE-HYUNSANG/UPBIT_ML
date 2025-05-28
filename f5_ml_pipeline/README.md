# f5_ml_pipeline

1분봉 기반 초단타 자동매매를 위한 머신러닝 파이프라인 구조입니다. 각 단계별 스크립트는 독립적으로 실행할 수 있으며 중간 산출물은 `ml_data/` 하위 폴더에 저장됩니다.

## 폴더 구조

```
f5_ml_pipeline/
│
├── 01_data_collect.py
├── 02_data_cleaning.py
├── 03_feature_engineering.py
├── 04_labeling.py
├── 05_split.py
├── 06_train.py
├── 07_eval.py
├── 08_predict.py
│
├── ml_data/
│   ├── 01_raw/
│   ├── 02_clean/
│   ├── 03_feature/
│   ├── 04_label/
│   ├── 05_split/
│   ├── 06_models/
│   ├── 07_eval/
│   └── 08_pred/
│
├── config/
│   └── train_config.yaml
│
├── utils.py
├── requirements.txt
└── README.md
```

### 단계별 설명
- **01_data_collect.py**: 원본 데이터 수집 및 저장
- **02_data_cleaning.py**: 결측값 보정과 데이터 타입 고정
- **03_feature_engineering.py**: 각종 지표 계산 후 피처 추가
- **04_labeling.py**: 매매 라벨 생성
- **05_split.py**: 학습/검증/테스트 데이터 분할
- **06_train.py**: 모델 학습 수행
- **07_eval.py**: 모델 평가 및 메트릭 저장
- **08_predict.py**: 예측 실행 및 결과 저장

### ml_data 폴더
단계별 산출 데이터는 다음 규칙으로 저장합니다.

| 단계 | 입출력 예시 |
|------|-------------|
| 데이터 수집 | `ml_data/01_raw/{symbol}_raw.parquet` |
| 데이터 정제 | `ml_data/02_clean/{symbol}_clean.parquet` |
| 피처 엔지니어링 | `ml_data/03_feature/{symbol}_feature.parquet` |
| 라벨링 | `ml_data/04_label/{symbol}_label.parquet` |
| 데이터 분할 | `ml_data/05_split/{symbol}_{part}.parquet` |
| 모델 | `ml_data/06_models/{symbol}_model.pkl` |
| 평가 | `ml_data/07_eval/{symbol}_metrics.json` |
| 예측 | `ml_data/08_pred/{symbol}_pred.parquet` |

### 설정 파일 관리
모델 학습 파라미터 등은 모두 `config/train_config.yaml`에서 관리합니다. 스크립트에서 이 파일을 읽어 동일한 파라미터를 사용하도록 합니다.

### 유틸리티 사용
공통 함수는 `utils.py`에 정의하여 각 단계에서 임포트하여 사용합니다.

### 실행 방법
필요 패키지를 먼저 설치합니다.

```bash
pip install -r requirements.txt
```

이후 각 스크립트를 순서대로 실행하여 파이프라인을 진행합니다.
