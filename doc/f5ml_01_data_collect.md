# F5ML_01_data_collect.py 사용법

`coin_list_data_collection.json`에 명시된 코인들을 매 분마다 호출하여
OHLCV, 호가, 체결, 시세 데이터를 수집합니다.
수집된 데이터는 `f5_ml_pipeline/ml_data/01_raw/<데이터종류>/` 폴더에
Parquet 형식으로 저장됩니다.

## 주요 기능
- `load_coin_list()` 함수가 모니터링 목록을 읽어 리스트를 반환합니다.
- 매 분 정각 이후 5초에 `collect_once()`가 한 번씩 호출되어 OHLCV, 호가, 체결, 시세를 다운로드합니다.
- `save_data()`가 기존 파일을 불러와 중복을 제거한 뒤 누적 저장합니다.
- 모든 과정은 `logs/data_collect.log`에 기록되어 누락 여부를 확인할 수 있습니다.

모니터링할 코인 목록은 `config/coin_list_data_collection.json`에 저장되며,
로그 파일은 `f5_ml_pipeline/logs/data_collect.log`로 분리되어 보관됩니다.

### 코드 구조
- `load_coin_list()` – 수집 대상 코인을 불러옵니다.【F:f5_ml_pipeline/01_data_collect.py†L57-L68】
- `collect_once()` – 한 번 실행으로 OHLCV, 호가 등 네 종류의 데이터를 모두 수집합니다.【F:f5_ml_pipeline/01_data_collect.py†L152-L177】
- `next_minute()` – 다음 분 시작 시각을 계산해 루프 타이밍을 맞춥니다.【F:f5_ml_pipeline/01_data_collect.py†L180-L183】
- `main()` – 무한 루프를 돌며 `collect_once()`를 호출합니다.【F:f5_ml_pipeline/01_data_collect.py†L186-L213】

다음과 같이 실행할 수 있습니다.
```bash
python f5_ml_pipeline/01_data_collect.py
```
스크립트는 파일 위치를 기준으로 코인 리스트를 찾으므로 실행 디렉터리에 상관없이
동일하게 동작합니다.
모든 경로는 스크립트의 위치를 기준으로 절대화되므로 어디서 실행해도 `f5_ml_pipeline/ml_data/` 아래에 데이터가 저장됩니다.
