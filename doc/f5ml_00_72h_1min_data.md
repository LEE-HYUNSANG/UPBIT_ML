# F5ML_00_72h_1min_data.py 사용법

`f1_f5_data_collection_list.json`에 명시된 코인들의 최근 72시간 1분봉 데이터를 한 번에 다운로드합니다.
파일은 `f5_ml_pipeline/ml_data/00_72h_1min_data/` 폴더에 `<코인ID>_rawdata.parquet` 형식으로 저장됩니다.
실행 시 기존 파일을 모두 삭제하고 최신 데이터로 교체합니다.

## 주요 기능
- `get_ohlcv_history()` – 각 코인에 대해 분할 호출로 72시간 분봉을 가져옵니다.【F:f5_ml_pipeline/00_72h_1min_data.py†L75-L98】
- `collect_all()` – 모든 코인의 데이터를 내려받아 저장합니다.【F:f5_ml_pipeline/00_72h_1min_data.py†L146-L173】

모든 시장의 데이터를 임시 폴더에 저장한 뒤 기존 파일을 삭제하고
`00_72h_1min_data` 디렉터리에 최신본을 유지합니다.

다음과 같이 실행합니다.
```bash
python f5_ml_pipeline/00_72h_1min_data.py
```

웹 대시보드(`app.py`)에서는 20분마다 이 스크립트를 자동 실행해
누락되었을 수 있는 데이터를 다시 내려받습니다. 실시간 수집 중
파일 손상이 있어도 주기적인 전체 갱신으로 복구할 수 있습니다.

## Troubleshooting

만약 기존 저장된 Parquet 파일을 읽지 못한다는 경고가 표시된다면 손상된 파일일 수 있습니다.
`save_data()`는 수집된 데이터를 임시 파일에 기록 후 원본을 교체하는 방식으로 저장하여
예기치 못한 중단 시에도 파일 손상을 최소화합니다.
그래도 읽기에 실패하면 기존 파일을 `<name>.corrupt.<timestamp>` 형식으로
백업한 뒤 새로 저장합니다.
