# F5ML_01_data_collect.py 사용법

`coin_list_data_collection.json` 파일에 지정된 코인 목록을 대상으로 1분 간격으로
OHLCV, 호가, 체결, 시세 데이터를 수집합니다. 결과 Parquet 파일은
`f5_ml_pipeline/ml_data/01_raw/<데이터종류>/` 폴더에 저장됩니다.

## 주요 기능
- `load_coin_list()` 함수가 모니터링 목록을 읽어 리스트를 반환합니다.
- 매 분 정각 이후 5초에 `collect_once()`가 한 번씩 호출되어 OHLCV, 호가, 체결, 시세를 다운로드합니다.
- `save_data()`가 기존 파일을 불러와 중복을 제거한 뒤 누적 저장합니다.
- 모든 과정은 `logs/data_collect.log`에 기록되어 누락 여부를 확인할 수 있습니다.

다음과 같이 실행할 수 있습니다.
```bash
python f5_ml_pipeline/01_data_collect.py
```
스크립트는 파일 위치를 기준으로 코인 리스트를 찾으므로 실행 디렉터리에 상관없이
동일하게 동작합니다.
모든 경로는 스크립트의 위치를 기준으로 절대화되므로 어디서 실행해도 `f5_ml_pipeline/ml_data/` 아래에 데이터가 저장됩니다.
