# F5ML_04_labeling.py 사용법

`f5_ml_pipeline/ml_data/03_feature/` 폴더의 피처 파일을 읽어 초단타 매매용 라벨을 생성합니다. 결과는
`f5_ml_pipeline/ml_data/04_label/` 폴더에 `{symbol}_label.parquet` 형식으로 저장됩니다.

## 라벨 기준
- **1 (익절)**: 미래 `horizon` 구간에서 고가가 진입가의 `(1 + thresh_pct)` 이상이면 1
- **-1 (손절)**: 미래 `horizon` 구간에서 저가가 진입가의 `(1 - thresh_pct)` 이하이면 -1
- **0 (중립)**: 위 두 조건을 모두 만족하지 못할 때 0

`horizon`은 기본 5분으로 고정되며, 파라미터 탐색 범위는 다음과 같습니다.

- `THRESH_LIST = [0.005, 0.006, 0.007]`
- `LOSS_LIST = [0.005, 0.006, 0.007]`

트레일링 스탑을 비활성화하려면 `trail_start_pct` 또는 `trail_down_pct` 값을
`None`으로 설정합니다. 이 경우 라벨링과 백테스트는 단순 TP/SL 규칙만 사용합니다.

## 실행 방법
```bash
python f5_ml_pipeline/04_labeling.py
```

모든 스크립트는 자신의 디렉터리를 기준으로 절대 경로를 계산하므로 어느 위치에서 실행해도 `f5_ml_pipeline/ml_data/` 아래에 결과가 저장됩니다.
실행 후 심볼별 `{symbol}_label.parquet` 파일이 생성됩니다.

## 변경 사항
버전 업데이트로 라벨 생성 로직이 NumPy의 `sliding_window_view`를 사용하도록 개선되어
대량 데이터 처리 속도가 향상되었습니다.
