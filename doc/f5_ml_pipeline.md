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
Formulas are parsed at runtime from `strategies_master_pruned.json`.
They are converted to Python expressions using the AST so logical chains keep
their intended precedence. Feature files from `ml_data/03_features/` are
labelled and written to `ml_data/04_labels/` using the same filenames.
Placeholder columns such as `entry_price`, `exit_price` and `peak` are created
when missing so backtests can reference them immediately. Column lookups use the
helper `_get_col` so missing fields fall back to sensible defaults. You can run
this step directly from the repository root using
`python f5_ml_pipeline/04_label.py`. The script automatically adjusts `sys.path`
so that `strategy_loader` is imported correctly.
