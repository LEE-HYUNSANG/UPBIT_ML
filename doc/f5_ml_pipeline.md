# F5 Machine Learning Pipeline

This directory contains scripts and data folders for training and evaluating ML models used by the trading system. Each numbered script corresponds to a pipeline step.

## 02_clean.py

`02_clean.py` cleans raw CSV files under `ml_data/01_raw` by filling missing values, normalizing column names and types, removing duplicates and zero rows, and writing the cleaned data as parquet files under `ml_data/02_clean`.
