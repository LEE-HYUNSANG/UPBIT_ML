# F5ML_00_yesterday_1min_data.py 사용법

`f1_f5_data_collection_list.json`에 명시된 코인들의 직전 24시간 1분봉 데이터를 한 번에 다운로드합니다.
파일은 `f5_ml_pipeline/ml_data/00_24ago_data/` 폴더에 Parquet 형식으로 저장됩니다.

## 주요 기능
- `get_ohlcv_history()` – 각 코인에 대해 분할 호출로 24시간 분봉을 가져옵니다.【F:f5_ml_pipeline/00_yesterday_1min_data.py†L77-L99】
- `collect_all()` – 모든 코인의 데이터를 내려받아 저장합니다.【F:f5_ml_pipeline/00_yesterday_1min_data.py†L144-L153】

다음과 같이 실행합니다.
```bash
python f5_ml_pipeline/00_yesterday_1min_data.py
```
