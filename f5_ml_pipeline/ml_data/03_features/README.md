# ③ 피처 엔지니어링 데이터

`03_features.py`에서 산출된 지표 컬럼이 포함된 Parquet 파일을 저장합니다.

생성되는 주요 컬럼은 다음과 같습니다.

- `ema_5`, `ema_20`, `ema_60`
- `atr_14`, `rsi_14`, `mfi_14`
- `bb_mid_20_2`, `bb_upper_20_2`, `bb_lower_20_2`
- `stoch_k_14`, `stoch_d_14`
- `vwap`, `psar`
- `tenkan_9`, `kijun_26`, `span_a`, `span_b`, `max_span`
- `ma_vol_20`, `max_high_20`, `min_low_20` 등 각종 rolling 지표
- `strength` (거래 강도 근사치)
- `buy_qty_5m`, `sell_qty_5m` (OHLCV만으로 계산 불가 – Collector 필요)

파일명은 `02_clean/`에 있는 원본과 동일하며 압축된 Parquet 포맷(`zstd`)으로 저장됩니다.
