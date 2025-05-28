# 05_split.py 사용법

`ml_data/04_label/` 폴더의 라벨 데이터를 읽어 시간순으로 학습, 검증, 테스트 세트로 분할합니다.
결과는 `ml_data/05_split/`에 `{symbol}_train.parquet`, `{symbol}_valid.parquet`, `{symbol}_test.parquet` 형식으로 저장됩니다.

기본 분할 비율은 학습 70%, 검증 20%, 테스트 10%이며, 필요한 경우 코드 상에서 비율을 변경할 수 있습니다.

## 실행 방법
```bash
python f5_ml_pipeline/05_split.py
```
