# F5ML_10_select_best_strategies.py 사용법

`ml_data/09_backtest/`에 저장된 `{symbol}_summary.json` 파일을 읽어
승률, 평균 수익률, Sharpe 지수, 최대 낙폭(MDD) 등 기준을 만족하는 전략만 선별합니다.
상위 전략들은 `ml_data/10_selected/selected_strategies.json`에 저장되며
실전 매수 모니터링 단계에서 이 파일을 로드하여 사용합니다.

스크립트가 완료되면 선택된 코인 심볼만 추출하여
`config/coin_list_monitoring.json`에도 저장됩니다.
파일 구조는 다음과 같습니다.

```json
[
    "KRW-BTC",
    "KRW-ETH",
    "KRW-XRP"
]
```

## 실행 방법
```bash
python f5_ml_pipeline/10_select_best_strategies.py
```

기본 필터링 조건과 정렬 기준은 스크립트 상단의 상수를 수정해 손쉽게 변경할 수 있습니다.
