# F5ML_00_yesterday_1min_data.py 사용법

`f1_f5_data_collection_list.json`에 명시된 코인들의 최근 72시간 1분봉 데이터를 한 번에 다운로드합니다.
파일은 `f5_ml_pipeline/ml_data/01_raw/` 폴더에 `<코인ID>_rawdata.parquet` 형식으로 저장됩니다. 실행 시 기존 폴더 내용은 모두 삭제됩니다.

## 주요 기능
- `get_ohlcv_history()` – 각 코인에 대해 분할 호출로 72시간 분봉을 가져옵니다.【F:f5_ml_pipeline/00_yesterday_1min_data.py†L84-L107】
- `collect_all()` – 모든 코인의 데이터를 내려받아 저장합니다.【F:f5_ml_pipeline/00_yesterday_1min_data.py†L155-L164】

다음과 같이 실행합니다.
```bash
python f5_ml_pipeline/00_yesterday_1min_data.py
```

## Troubleshooting

만약 기존 저장된 Parquet 파일을 읽지 못한다는 경고가 표시된다면 손상된 파일일 수 있습니다.
`save_data()` 함수는 이런 경우 파일을 자동으로 삭제하므로 다음 실행에서 새로 다운로드한 데이터가 저장됩니다.
