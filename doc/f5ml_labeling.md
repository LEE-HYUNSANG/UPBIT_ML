# F5ML_04_labeling.py 사용법

`ml_data/03_feature/` 폴더의 피처 파일을 읽어 초단타 매매용 라벨을 생성합니다. 결과는
`ml_data/04_label/` 폴더에 `{symbol}_label.parquet` 형식으로 저장됩니다.

## 라벨 기준
- **1 (익절)**: 미래 `horizon` 구간에서 고가가 진입가의 `(1 + thresh_pct)` 이상이면 1
- **-1 (손절)**: 미래 `horizon` 구간에서 저가가 진입가의 `(1 - thresh_pct)` 이하이면 -1
- **0 (중립)**: 위 두 조건을 모두 만족하지 못할 때 0

기본값은 `horizon=30`, `thresh_pct=0.003`(0.3%)입니다.

트레일링 스탑을 비활성화하려면 `trail_start_pct` 또는 `trail_down_pct` 값을
`None`으로 설정합니다. 이 경우 라벨링과 백테스트는 단순 TP/SL 규칙만 사용합니다.

## 실행 방법
```bash
python f5_ml_pipeline/04_labeling.py
```

실행 후 심볼별 `{symbol}_label.parquet` 파일이 생성됩니다.
