# 폴더/프로세스 설명

This folder contains a step-by-step ML pipeline for the trading system.

```
ml_data/
  01_raw/        # 원본 csv (업비트 1분봉 OHLCV)
  02_clean/      # 클린 parquet (결측/중복/타입정리)
  03_features/   # 피처 parquet (지표 산출 후)
```

Scripts:

1. `01_fetch_market.py` – retrieve raw market data
2. `02_clean.py` – clean data and output Parquet
3. `03_features.py` – add technical indicators to cleaned data

Common helper functions live in `F5_utils.py` which currently exposes a
`now()` function returning the current epoch timestamp.
