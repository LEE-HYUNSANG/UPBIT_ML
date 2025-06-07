# F5ML_99_100day_1min_data.py 사용법

`f1_f5_data_collection_list.json`에 명시된 코인들의 최근 100일 1분봉 데이터를 한 번에 다운로드합니다. 결과 파일은 `f5_ml_pipeline/ml_data/99_100day_1min_data/` 디렉터리에 `<코인ID>_rawdata.parquet` 형식으로 저장됩니다. 실행 시 기존 데이터를 모두 삭제하고 각 코인의 행 수가 144,000개가 될 때까지 반복 수집합니다.

## 주요 기능
- `get_ohlcv_history()` – 100일치 분봉을 순차적으로 가져옵니다.【F:f5_ml_pipeline/99_100day_1min_data.py†L58-L82】
- `collect_markets()` – 임시 폴더에 저장 후 정상 파일만 최종 위치로 이동합니다.【F:f5_ml_pipeline/99_100day_1min_data.py†L150-L172】

아래와 같이 수동으로 실행합니다.
```bash
python f5_ml_pipeline/99_100day_1min_data.py
```
