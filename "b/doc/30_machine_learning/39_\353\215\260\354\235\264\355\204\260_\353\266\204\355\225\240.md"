# F5ML_05_split.py 사용법

`f5_ml_pipeline/ml_data/04_label/` 폴더의 라벨 데이터를 읽어 시간순으로 학습, 검증, 테스트 세트로 분할합니다.
결과는 `f5_ml_pipeline/ml_data/05_split/` 폴더에 저장되며 파일 이름은 `{symbol}_train.parquet` 등입니다.

기본 분할 비율은 학습 70%, 검증 20%, 테스트 10%이며, 함수 `time_split()`의 인자로 조정할 수 있습니다.
라벨 파일 하나를 처리하는 로직은 `process_file()` 함수에 구현되어 있습니다.
모든 동작 기록은 `logs/F5_ml_split.log`에 남습니다.

## 실행 방법
```bash
python f5_ml_pipeline/05_split.py
```

경로는 스크립트 위치를 기준으로 계산되므로 현재 작업 디렉터리와 상관없이
동일한 폴더 구조(`f5_ml_pipeline/ml_data/04_label/`, `f5_ml_pipeline/ml_data/05_split/`)에 결과가 저장됩니다.
