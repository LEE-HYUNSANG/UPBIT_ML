# F5ML_01_data_collect.py 사용법

`coin_list_data_collection.json` 파일에 지정된 코인 목록을 대상으로 1분 간격으로
OHLCV, 호가, 체결, 시세 데이터를 수집합니다. 결과 Parquet 파일은
`f5_ml_pipeline/ml_data/01_raw/<데이터종류>/` 폴더에 저장됩니다.

## 주요 기능
- 코인 리스트를 읽어 매 분 정각 이후 5초가 지난 시점에 데이터를 요청합니다.
- 기존 파일이 있으면 데이터를 누적 저장하며 `timestamp`와 `market` 등을 기준으로
  중복을 제거합니다.
- 오류나 누락 내역은 `logs/data_collect.log`에 기록됩니다.

다음과 같이 실행할 수 있습니다.
```bash
python f5_ml_pipeline/01_data_collect.py
```
스크립트는 파일 위치를 기준으로 코인 리스트를 찾으므로 실행 디렉터리에 상관없이
동일하게 동작합니다.
모든 경로는 스크립트의 위치를 기준으로 절대화되므로 어디서 실행해도 `f5_ml_pipeline/ml_data/` 아래에 데이터가 저장됩니다.
