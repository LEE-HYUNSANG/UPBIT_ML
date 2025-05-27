# Upbit Minute Data Collector

This utility fetches 1-minute OHLCV data in bulk from Upbit.

```bash
python upbit_coin_data/collector.py
```

The script automatically:

1. Retrieves all KRW market tickers and filters for coins priced between
   500 and 25,000 KRW.
2. For each selected coin it downloads 90 days of 1 minute candles in
   batches of 200 and saves the result under `upbit_coin_data/` as
   `<MARKET>_YYYYMMDD_HHMMSS-YYYYMMDD_HHMMSS.csv`.
3. Requests are rate limited (max 10 per second) and retried on `429` or
   server errors.

To collect a specific set of coins, edit `SELECTED_MARKETS` at the top of
`collector.py` with a list of tickers such as `["KRW-BTC", "KRW-ETH"]`. When
this list is non-empty, the automatic price filter is skipped.

Logs are written to `upbit_coin_data/collector.log`.
