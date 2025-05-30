# f5_ml_pipeline 머신러닝 파이프라인

이 디렉터리는 1분봉 데이터를 이용한 초단타 매매 모델을 구축하기 위한 스크립트를 모아 둔 곳입니다.
각 단계는 독립적으로 실행할 수 있으며 산출물은 `ml_data/` 아래에 순차적으로 저장됩니다.
복잡한 프로그래밍 지식이 없어도 파이프라인 흐름을 이해하고 실행할 수 있도록 간단한 사용 방법을 안내합니다.

## 전체 흐름
1. **00_Before_Coin.py** – 가격과 거래대금 조건을 만족하는 코인의 원시 데이터를 수집합니다.
2. **01_data_collect.py** – OHLCV 데이터를 다운로드합니다.
3. **02_data_cleaning.py** – 결측치 보정과 데이터 형식을 통일합니다.
4. **03_feature_engineering.py** – 기술적 지표를 계산해 피처를 추가합니다.
5. **04_labeling.py** – 매매 신호 생성을 위한 라벨을 만듭니다.
6. **05_split.py** – 학습/검증/테스트 세트로 시간순 분할합니다.
7. **06_train.py** – 설정 파일을 읽어 모델을 학습합니다.
8. **07_eval.py** – 학습된 모델의 성능을 평가합니다.
9. **08_predict.py** – 모델을 이용해 예측 값을 생성합니다.
10. **09_backtest.py** – 예측 결과로 간단한 백테스트를 수행합니다.
11. **10_select_best_strategies.py** – 백테스트 성과가 좋은 전략을 자동 선별합니다.

## 폴더 구조 예시
```
f5_ml_pipeline/
│
├── 00_Before_Coin.py
├── 01_data_collect.py
├── 02_data_cleaning.py
├── 03_feature_engineering.py
├── 04_labeling.py
├── 05_split.py
├── 06_train.py
├── 07_eval.py
├── 08_predict.py
├── 09_backtest.py
├── 10_select_best_strategies.py
│
├── ml_data/
│   ├── 00_back_raw/
│   ├── 01_raw/
│   ├── 02_clean/
│   ├── 03_feature/
│   ├── 04_label/
│   ├── 05_split/
│   ├── 06_models/
│   ├── 07_eval/
│   ├── 08_pred/
│   ├── 09_backtest/
│   └── 10_selected/
│
├── config/
│   └── train_config.yaml
│
├── utils.py
├── requirements.txt
└── README.md
```

### 데이터 저장 규칙
파이프라인 단계별 결과 파일은 다음과 같은 규칙으로 저장됩니다.

| 단계 | 입출력 예시 |
|------|-------------|
| 원시 수집 | `ml_data/00_back_raw/{symbol}_1min.csv` |
| 데이터 수집 | `ml_data/01_raw/{symbol}_raw.parquet` |
| 데이터 정제 | `ml_data/02_clean/{symbol}_clean.parquet` |
| 피처 생성 | `ml_data/03_feature/{symbol}_feature.parquet` |
| 라벨링 | `ml_data/04_label/{symbol}_label.parquet` |
| 데이터 분할 | `ml_data/05_split/{symbol}_{part}.parquet` |
| 모델 | `ml_data/06_models/{symbol}_model.pkl` |
| 평가 | `ml_data/07_eval/{symbol}_metrics.json` |
| 예측 | `ml_data/08_pred/{symbol}_pred.parquet` |
| 백테스트 | `ml_data/09_backtest/{symbol}_summary.json` |
| 전략 선정 | `ml_data/10_selected/selected_strategies.json` |

### 설정 및 공통 함수
모델 파라미터는 `f5_ml_pipeline/config/train_config.yaml`에서 관리합니다.
모든 스크립트는 해당 파일을 읽어 동일한 설정을 사용합니다.
자주 사용하는 함수는 `utils.py`에 모아 두었으니 필요한 단계에서 불러와 사용합니다.

### 실행 방법
필요한 패키지를 먼저 설치합니다.
```bash
pip install -r requirements.txt
```
그 후 원하는 단계의 스크립트를 실행하면 됩니다.
순서대로 실행하면 전체 파이프라인을 경험할 수 있습니다.
각 단계의 자세한 설명은 `doc/` 폴더의 개별 문서를 참고하세요.
