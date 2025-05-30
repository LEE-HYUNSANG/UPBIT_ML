# F5ML_02_data_cleaning.py 사용법

`f5_ml_pipeline/ml_data/01_raw/` 폴더(및 하위 디렉터리)에 있는 업비트 원본 데이터를
머신러닝에 적합한 형식으로 정제하여 `f5_ml_pipeline/ml_data/02_clean/` 하위에 저장합니다.
`ohlcv`, `ticker`, `trades`, `orderbook` 등 타입별 폴더 구조를 인식하며,
같은 심볼의 여러 파일이 있을 경우 자동 병합 후 하나의 결과 파일을 생성합니다.

## 주요 기능
- 폴더와 하위 폴더의 모든 CSV/XLSX/Parquet 파일을 자동 탐색합니다.
- 동일 심볼의 여러 파일이 존재하면 하나로 병합해 저장합니다.
- `ohlcv`를 기준으로 `ticker`와 `orderbook`은 가장 가까운 시각의 데이터를
  선택해 병합합니다.
- `trades` 데이터는 1분 단위로 가격 평균과 거래량 합계를 집계한 후 병합합니다.
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

실행 후 `f5_ml_pipeline/ml_data/02_clean/<type>/` 폴더에 `{symbol}_clean.parquet` 파일이 생성됩니다.
데이터가 크게 줄어든 경우 경고가 표시됩니다.
모든 스크립트는 자신의 폴더를 기준으로 절대 경로를 계산하므로 어느 위치에서 실행해도 `f5_ml_pipeline/ml_data/` 아래에 결과가 저장됩니다.
