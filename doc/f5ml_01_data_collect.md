# F5ML_01_data_collect.py 사용법

`f1_f5_data_collection_list.json`에 명시된 코인들을 매 분마다 호출하여
**OHLCV** 데이터만 수집합니다.
수집된 파일은 `f5_ml_pipeline/ml_data/01_raw/` 폴더에
`<코인ID>_rawdata.parquet` 이름으로 누적 저장됩니다.

## 주요 기능
- `load_coin_list()` 함수가 모니터링 목록을 읽어 리스트를 반환합니다.
- 1분봉이 완료된 뒤 5초 후에 `collect_once()`가 호출되어 OHLCV를 다운로드합니다.
- `save_data()`가 기존 파일을 불러와 중복을 제거한 뒤 누적 저장합니다.
- 새로 저장할 때 **72시간** 이전의 행은 자동으로 삭제되어 항상 최근 72시간치만 유지합니다.
- 모든 과정은 `logs/F5_data_collect.log`에 기록되어 누락 여부를 확인할 수 있습니다.

모니터링할 코인 목록은 `config/f1_f5_data_collection_list.json`에 저장되며,
로그 파일은 `logs/F5_data_collect.log`로 분리되어 보관됩니다.

### 코드 구조
- `load_coin_list()` – 수집 대상 코인을 불러옵니다.【F:f5_ml_pipeline/01_data_collect.py†L57-L68】
- `collect_once()` – 지정된 코인의 OHLCV를 저장합니다.【F:f5_ml_pipeline/01_data_collect.py†L160-L170】
- `next_minute()` – 다음 분 시작 시각을 계산해 루프 타이밍을 맞춥니다.【F:f5_ml_pipeline/01_data_collect.py†L173-L176】
- `main()` – 무한 루프를 돌며 `collect_once()`를 호출합니다.【F:f5_ml_pipeline/01_data_collect.py†L179-L206】

다음과 같이 실행할 수 있습니다.
```bash
python f5_ml_pipeline/01_data_collect.py
```
스크립트는 파일 위치를 기준으로 코인 리스트를 찾으므로 실행 디렉터리에 상관없이
동일하게 동작합니다.
모든 경로는 스크립트의 위치를 기준으로 절대화되므로 어디서 실행해도 `f5_ml_pipeline/ml_data/` 아래에 데이터가 저장됩니다.

## Troubleshooting

간혹 예기치 못한 종료나 디스크 문제로 기존 Parquet 파일이 손상될 수 있습니다.
`save_data()` 함수는 파일을 읽지 못하면 경고를 남기고 해당 파일을 자동으로 삭제합니다.
다음 실행에서 새 파일이 생성되므로 수집이 계속 진행될 수 있습니다.
