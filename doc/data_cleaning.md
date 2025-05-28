# 02_data_cleaning.py 사용법

`ml_data/01_raw/` 폴더에 있는 업비트 1분봉 원본 CSV(XLSX) 파일을
머신러닝에 적합한 형식으로 정제하여 `ml_data/02_clean/` 하위에 저장합니다.

## 주요 기능
- 폴더 내 모든 CSV/XLSX 파일을 자동 탐색해 처리합니다.
- 파일명에서 심볼을 추출해 `{symbol}_clean.parquet` 형식으로 저장합니다.
- 업비트 원본 컬럼(`opening_price`, `high_price`, `low_price`, `trade_price`,
  `candle_acc_trade_volume`, `candle_date_time_utc`)을 각각 `open`, `high`, `low`,
  `close`, `volume`, `timestamp`으로 리네임합니다.
- `timestamp` 컬럼은 ISO8601 문자열을 UTC 기준 `datetime`으로 변환하며 1분
  간격을 보장합니다.
- 결측 타임스탬프는 새 행을 생성해 보간하고, OHLC 결측치는 앞/뒤 값으로 채웁니다.
- 가격/거래량이 모두 0인 행, 음수 값, 중복 타임스탬프는 제거합니다.
- 삭제 및 보정 전후의 행 수가 `logs/ml_clean.log`에 기록됩니다.
- OHLC 컬럼이 일부 없는 파일도 오류 없이 처리합니다.
- 파케이 저장이 불가능한 환경에서는 같은 이름의 CSV로 대체 저장합니다.

## 실행 방법
```bash
python f5_ml_pipeline/02_data_cleaning.py
```

실행 후 `ml_data/02_clean/` 폴더에 `{symbol}_clean.parquet` 파일이 생성됩니다.
데이터가 크게 줄어든 경우 경고가 표시됩니다.
