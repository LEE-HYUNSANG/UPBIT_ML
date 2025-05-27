# F5 Machine Learning Pipeline

This directory contains scripts and data folders for training and evaluating ML models used by the trading system. Each numbered script corresponds to a pipeline step.

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
