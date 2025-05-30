# F5ML_05_split.py 사용법

`f5_ml_pipeline/ml_data/04_label/` 폴더의 라벨 데이터를 읽어 시간순으로 학습, 검증, 테스트 세트로 분할합니다.
결과는 `f5_ml_pipeline/ml_data/05_split/`에 `{symbol}_train.parquet`, `{symbol}_valid.parquet`, `{symbol}_test.parquet` 형식으로 저장됩니다.

기본 분할 비율은 학습 70%, 검증 20%, 테스트 10%이며 필요에 따라 인자를 조정할 수 있습니다.

### 코드 구조
- `time_split()` – 데이터프레임을 시간순으로 나눠 세 개의 데이터프레임을 반환합니다.【F:f5_ml_pipeline/05_split.py†L40-L50】
- `process_file()` – 단일 파일을 읽어 `time_split()` 후 결과를 저장합니다.【F:f5_ml_pipeline/05_split.py†L53-L81】
- `main()` – `04_label` 폴더의 모든 Parquet 파일에 대해 반복 호출합니다.【F:f5_ml_pipeline/05_split.py†L84-L97】
로그는 `f5_ml_pipeline/logs/ml_split.log`에 남습니다.

## 실행 방법
```bash
python f5_ml_pipeline/05_split.py
```

경로는 스크립트 위치를 기준으로 계산되므로 현재 작업 디렉터리와 상관없이
동일한 폴더 구조(`f5_ml_pipeline/ml_data/04_label/`, `f5_ml_pipeline/ml_data/05_split/`)에 결과가 저장됩니다.
