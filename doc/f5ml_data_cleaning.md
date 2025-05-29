# F5ML_02_data_cleaning.py 사용법

`ml_data/01_raw/` 폴더 아래의 `ohlcv`, `ticker`, `trades`, `orderbook`
데이터를 자동으로 탐색합니다. 심볼별로 여러 날짜의 CSV/XLSX/Parquet 파일을
모두 병합한 뒤, OHLCV의 `market`과 `timestamp`를 기준으로 나머지 데이터와
1초 허용 오차 내에서 결합하여 `ml_data/02_clean/`에 저장합니다.

## 주요 기능
- `ohlcv`, `ticker`, `trades`, `orderbook` 하위 폴더를 모두 탐색합니다.
- 동일 심볼의 여러 파일을 모아 하나의 데이터프레임으로 병합합니다.
- OHLCV의 `timestamp` 기준으로 다른 타입 데이터를 1초 이내에서 `merge_asof`합니다.
- 파일명에서 심볼을 추출해 `{symbol}_clean.parquet` 형식으로 저장합니다.
- 업비트 원본 컬럼(`opening_price`, `high_price`, `low_price`, `trade_price`,
  `candle_acc_trade_volume`, `candle_date_time_utc`)을 각각 `open`, `high`, `low`,
  `close`, `volume`, `timestamp`으로 리네임합니다.
- 결측 타임스탬프 행 제거, 시계열 정렬 및 중복 제거 후 필요한 경우 1분 단위로 보간합니다.
- 삭제 및 보정 전후의 행 수가 `logs/ml_clean.log`에 기록됩니다.
- 파케이 저장이 불가능한 환경에서는 같은 이름의 CSV로 대체 저장합니다.
- 동일한 이름의 컬럼이 여러 개 존재하면 값이 있는 컬럼을 우선하여 병합합니다.

## 실행 방법
```bash
python f5_ml_pipeline/02_data_cleaning.py
```

실행 후 `ml_data/02_clean/<type>/` 폴더에 `{symbol}_clean.parquet` 파일이 생성됩니다.
데이터가 크게 줄어든 경우 경고가 표시됩니다.
