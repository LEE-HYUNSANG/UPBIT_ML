# 03_feature_engineering.py 사용법

`ml_data/02_clean/` 폴더의 정제 데이터를 읽어 주요 지표를 계산한 후
`ml_data/03_feature/`에 저장합니다.

데이터는 `open`, `high`, `low`, `close`, `volume`, `timestamp` 컬럼이 존재하는
형태여야 합니다. 컬럼 표준화는 [02_data_cleaning.py](data_cleaning.md)에서
처리됩니다.

## 추가되는 지표
- `ema5`: 5분 지수이동평균
- `ema20`: 20분 지수이동평균
- `rsi14`: 14분 상대강도지수
- `atr14`: 14분 평균진폭
- `vol_ratio`: 최근 거래량 대비 비율
- `stoch_k`: 스토캐스틱 %K (14, 3)

실행 후 각 심볼별 `{symbol}_feature.parquet` 파일이 생성됩니다.
