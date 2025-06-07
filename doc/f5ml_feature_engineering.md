# F5ML_03_feature_engineering.py 사용법

`f5_ml_pipeline/ml_data/02_clean/` 폴더의 정제 데이터를 읽어 주요 지표를 계산한 후
`f5_ml_pipeline/ml_data/03_feature/`에 저장합니다.

데이터는 `open`, `high`, `low`, `close`, `volume`, `timestamp` 컬럼이 존재하는
형태여야 합니다. 컬럼 표준화는 [02_data_cleaning.py](f5ml_data_cleaning.md)에서
처리됩니다.

## 추가되는 지표
- `ema5`, `ema8`, `ema13`, `ema20`, `ema21`, `ema60`, `ema120` 및 `sma5`, `sma20`
  : 다양한 이동평균과 교차 신호(`ema_gc`, `ema_dc`)
- `rsi7`, `rsi14`, `rsi21`: RSI 지표와 과매수/과매도 플래그
- `atr14`: 14분 평균진폭
- `pct_change_1m`, `pct_change_5m`, `pct_change_10m`, `mom10`, `roc10`: 변동률과 모멘텀
- `vol_ratio`, `vol_ratio_5`: 거래량 비율과 증감률
- `stoch_k7`, `stoch_d7`, `stoch_k14`, `stoch_d14`: 스토캐스틱 지표
- `macd`, `macd_signal`, `macd_hist`: MACD(12,26,9)
- `mfi14`: 14분 자금 흐름 지수
- `adx14`: 14분 ADX 추세 강도
- `cci14`: 상품채널지수
- `bb_mid`, `bb_upper`, `bb_lower`, `bb_width`, `bb_dist`: 볼린저 밴드와 변동성(`volatility14`, `anomaly`)
- `vwap`: 거래량 가중 평균가
- `obv`: 온밸런스 볼륨
- 여러 캔들 패턴과 시간 관련 파생 컬럼

실행 후 각 심볼별 `{symbol}_feature.parquet` 파일이 생성됩니다.
모든 스크립트는 자기 디렉터리 기준 절대 경로를 사용하므로 실행 위치와 관계없이 `f5_ml_pipeline/ml_data/` 하위에 결과가 저장됩니다.
