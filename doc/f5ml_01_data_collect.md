# F5ML_01_data_collect.py 사용법

`f1_f5_data_collection_list.json`에 명시된 코인들을 매 분마다 호출하여
**OHLCV** 데이터만 수집합니다. 최신 분봉은
`f5_ml_pipeline/ml_data/00_now_1min_data/` 폴더에 저장되며,
기존 Raw 데이터(`01_raw`)와 병합되어 누락된 최근 1시간 분봉까지 자동 보완됩니다.

## 주요 기능
- `load_coin_list()` 함수가 모니터링 목록을 읽어 리스트를 반환합니다.
- 1분봉이 완료된 뒤 5초 후에 `collect_once()`가 호출되어 OHLCV를 다운로드합니다.
- `save_data()`가 기존 파일을 불러와 중복을 제거한 뒤 누적 저장합니다.
- `fill_last_hour()`가 최근 1시간 데이터의 공백을 확인하고 필요한 분봉을 추가합니다.
- 수집된 데이터는 계속 누적되며 자동 삭제는 이루어지지 않습니다.
- 모든 과정은 `logs/F5_data_collect.log`에 기록되어 누락 여부를 확인할 수 있습니다.

모니터링할 코인 목록은 `config/f1_f5_data_collection_list.json`에 저장되며,
로그 파일은 `logs/F5_data_collect.log`로 분리되어 보관됩니다.

### 코드 구조
- `load_coin_list()` – 수집 대상 코인을 불러옵니다.【F:f5_ml_pipeline/01_data_collect.py†L39-L47】
- `collect_once()` – 지정된 코인의 OHLCV를 저장합니다.【F:f5_ml_pipeline/01_data_collect.py†L157-L167】
- `next_minute()` – 다음 분 시작 시각을 계산해 루프 타이밍을 맞춥니다.【F:f5_ml_pipeline/01_data_collect.py†L172-L175】
- `main()` – 무한 루프를 돌며 `collect_once()`를 호출합니다.【F:f5_ml_pipeline/01_data_collect.py†L178-L206】

다음과 같이 실행할 수 있습니다.
```bash
python f5_ml_pipeline/01_data_collect.py
```
스크립트는 파일 위치를 기준으로 코인 리스트를 찾으므로 실행 디렉터리에 상관없이
동일하게 동작합니다.
모든 경로는 스크립트의 위치를 기준으로 절대화되므로 어디서 실행해도 `f5_ml_pipeline/ml_data/` 아래에 데이터가 저장됩니다.

## Troubleshooting

간혹 예기치 못한 종료나 디스크 문제로 기존 Parquet 파일이 손상될 수 있습니다.
`save_data()` 함수는 잠금 파일을 사용해 동시 접근을 방지하며, 임시 파일에 저장한 후
원본을 교체(atomic replace)하여 손상 가능성을 최소화합니다.
기존 파일을 읽지 못할 경우 바로 삭제하지 않고 `<name>.corrupt.<timestamp>` 형식으로
이름을 변경해 백업한 뒤 새 파일을 저장하므로 데이터 손실 위험을 줄였습니다.
