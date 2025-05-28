# 02_data_cleaning.py 사용법

`ml_data/01_raw/` 폴더에 있는 원본 CSV 또는 XLSX 파일을 정제하여
`ml_data/02_clean/` 폴더로 저장하는 스크립트입니다.

## 주요 기능
- 폴더 내 모든 CSV/XLSX 파일을 자동 탐색해 처리합니다.
- 파일명에서 심볼을 추출해 `{symbol}_clean.parquet` 형식으로 저장합니다.
- `timestamp` 컬럼을 기준으로 1분 단위 연속성을 맞추고 결측치는 앞/뒤 값으로 보간합니다.
- 가격 또는 거래량이 음수이거나 0인 행, 중복 타임스탬프는 삭제합니다.
- 처리 결과와 삭제된 행 수 등은 `logs/ml_clean.log`에 기록됩니다.
- 파케이 저장이 불가능한 환경에서는 같은 이름의 CSV로 대체 저장합니다.

## 실행 방법
```bash
python f5_ml_pipeline/02_data_cleaning.py
```

실행 후 `ml_data/02_clean/` 폴더에 심볼별 파일이 생성됩니다.
