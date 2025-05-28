<<<<<<< HEAD
# F5 Machine Learning Pipeline

This directory contains scripts and data folders for training and evaluating ML models used by the trading system. Each numbered script corresponds to a pipeline step.

All pipeline logs are written to `f5_ml_pipeline/ml_data/09_logs` as
`mllog_<YYYYMMDDHHMMSS>.log`. When a log exceeds 1 MB it rotates to a new file.
Each message includes the step identifier like `[ML_01]` for `01_fetch_market.py`.

## 01_fetch_market.py
Retrieves 1 minute OHLCV data for the last 90 days using the Upbit REST API. The script:

- Automatically discovers all KRW markets.
- Filters symbols priced between 500 and 25,000 won using `/v1/ticker`.
- Downloads complete candle data via `/v1/candles/minutes/1` respecting rate limits.
- Saves each market as a CSV file under `f5_ml_pipeline/ml_data/01_raw/`.

The script depends on the `tqdm` package for progress bars. Install requirements
via `pip install -r requirements.txt` and run the script to start collection.

## 02_clean.py
Cleans raw market CSVs and outputs Parquet files to `ml_data/02_clean/`.
Column names returned by the Upbit API (e.g. `trade_price`, `opening_price`)
are automatically normalized to the standard `close`, `open`, `high`, `low`
and `volume` fields. This step relies on the `pyarrow` package for Parquet
support. Install requirements via `pip install -r requirements.txt` before
running the script.
## 03_features.py
Generates technical indicator columns from the cleaned OHLCV Parquet files found in `ml_data/02_clean/`.
The resulting feature sets are saved to `ml_data/03_features/` with the same filenames.
The script uses helper functions in `indicators.py` to calculate EMA, ATR, RSI,
Bollinger Bands, Stochastic, VWAP, MFI, Parabolic SAR and Ichimoku lines. It
also generates rolling highs/lows, volume averages, shifted spans
(`span_a_26`, `span_b_26`) and a combined `maxspan`. Placeholder fields that
depend on trade history (e.g. `buy_qty_5m`, `sell_qty_5m`) are filled with `NaN`
so they can later be merged with collector output.

You can run this step directly from the repository root using
`python f5_ml_pipeline/03_features.py`. The script automatically adjusts
`sys.path` so that imports from `indicators.py` resolve correctly.

## 04_label.py
Adds buy and sell label columns based on predefined strategy formulas.
The formulas are defined in `strategies_master_pruned.json` and parsed at
runtime so new strategies can be added without modifying the code. Feature
files from `ml_data/03_features/` are labelled and written to
`ml_data/04_labels/` using the same filenames. Placeholder columns such as
`entry_price`, `exit_price` and `peak` are created when missing so backtests can
reference them immediately. The formulas are parsed with Python's AST so boolean
`and`/`or` operators are safely converted to bitwise operations. Missing columns
referenced in the formulas are handled via the `_get_col` helper. You can run
this step directly from the repository root using `python f5_ml_pipeline/04_label.py`.
The script automatically adjusts `sys.path` so that `strategy_loader` is
imported correctly.
## 05_split.py
Splits each labelled dataset under `ml_data/04_labels/` into chronological training,
validation and test sets. The default ratios are 70% train, 15% validation and
15% test. Files are saved to `ml_data/05_split/` with the original filename
plus `_train`, `_val` or `_test` suffixes. The script ensures each dataset
contains at least one row when possible and logs progress for every file.
Run `python f5_ml_pipeline/05_split.py` after labels are generated with `04_label.py`.

## 06_optuna_tpe.py
Performs hyperparameter optimisation of a LightGBM model using Optuna's
TPE sampler. For every symbol and label column the training and validation
splits under `ml_data/05_split/` are loaded and tuned. After optimisation the
model is retrained on the combined train and validation data using the best
parameters and several artefacts are written to `ml_data/06_models/`:

- `{symbol}_{label}_best_params.json` – chosen hyperparameters
- `{symbol}_{label}_model.pkl` – trained model file
- `{symbol}_{label}_optuna_study.pkl` – Optuna study for later analysis
- `{symbol}_{label}_feature_importance.csv` – sorted feature importances
- `optuna_tuning_summary.csv` – summary table of all tuning runs

Execute it from the repository root with `python f5_ml_pipeline/06_optuna_tpe.py`.
This step depends on the `optuna`, `lightgbm`, `scikit-learn` and `joblib`
packages which are included in `requirements.txt`.

## 07_train_lgbm.py
Retrains LightGBM models using the best hyperparameters discovered in the
previous tuning step. The script loads each `{symbol}_train.parquet`,
`{symbol}_val.parquet` and `{symbol}_test.parquet` file from
`ml_data/05_split/` and combines the train and validation sets for final
training. Parameters are read from `{symbol}_{label}_best_params.json` and the
resulting model is saved to `ml_data/06_models/` as
`{symbol}_{label}_model.pkl`.

A small evaluation against the test split is performed using AUC, accuracy and
F1 metrics. The scores are stored next to the model in a
`{symbol}_{label}_metrics.json` file together with a CSV of sorted feature
importances. If the hyperparameter JSON is missing or malformed, the symbol is
skipped and a warning is printed.

Run it from the repository root with `python f5_ml_pipeline/07_train_lgbm.py`.

## 08_calibrate.py
Calibrates predicted probabilities of the trained models with isotonic regression.
Validation and test splits under `ml_data/05_split/` are loaded for each symbol.
The calibration model is fitted on validation predictions and evaluated on the
 test set. Metrics before and after calibration along with the chosen threshold
are stored in `ml_data/06_models/` using the filenames
`{symbol}_{label}_calib.pkl`, `{symbol}_{label}_calib_metrics.json` and
`{symbol}_{label}_thresh.json`.
Run it from the repository root with `python f5_ml_pipeline/08_calibrate.py`.

## 09_backtest.py
Performs a simple backtest using the calibrated models and test splits found in
`ml_data/05_split/`. For each symbol and strategy pair the script:

- Loads the trained model, calibration object and threshold from
  `ml_data/06_models/`.
- Generates probability predictions on the test set and applies the calibration
  model and threshold to decide entry and exit signals.
- Simulates long trades where a buy signal opens a position and a sell signal
  closes it.
- Writes the trade log as `{symbol}_{strategy}_trades.csv` and a KPI summary as
  `{symbol}_{strategy}_backtest_summary.json` under `ml_data/08_metrics/`.

Invoke the step with `python f5_ml_pipeline/09_backtest.py`.
=======
# f5_ml_pipeline 구조

이 문서는 1분봉 초단타 매매를 위한 머신러닝 파이프라인 구조를 설명합니다. 스크립트는 단계별로 분리되어 있으며 산출물은 `f5_ml_pipeline/ml_data/` 하위에 저장됩니다.

## 폴더 구성

- `01_data_collect.py` 데이터 수집
- `02_data_cleaning.py` 데이터 전처리
- `03_feature_engineering.py` 지표 계산
- `04_labeling.py` 라벨 생성
- `05_split.py` 학습/검증/테스트 분할
- `06_train.py` 모델 학습
- `07_eval.py` 모델 평가
- `08_predict.py` 예측 수행
- `ml_data/` 단계별 데이터 저장 폴더
- `config/train_config.yaml` 학습 설정 파일
- `utils.py` 공통 함수

## 사용 방법

필요 패키지는 `f5_ml_pipeline/requirements.txt`를 통해 설치합니다.
각 스크립트는 독립적으로 실행할 수 있으며, 설정은 `train_config.yaml`을 참고합니다.
>>>>>>> f29a68e968ce4a19d6ee38ac4fe851cbeeaededb
