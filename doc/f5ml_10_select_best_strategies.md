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

변경 사항은 `logs/select_best_strategies.log` 파일에도 기록되어
모니터링 목록 갱신 여부를 확인할 수 있습니다. 최신 버전은 스캔 시작과
요약 파일 개수, 각 후보의 채택 여부, 최종 저장된 심볼 목록까지 모두
남기므로 선별 과정이 명확하게 보입니다.

조건을 만족하는 전략이 하나도 없으면 두 파일은 빈 리스트 `[]`로 덮어써
이전 결과가 남지 않도록 합니다.

## 실행 방법
```bash
python f5_ml_pipeline/10_select_best_strategies.py
```

기본 필터링 조건과 정렬 기준은 스크립트 상단의 상수를 수정해 손쉽게 변경할 수 있습니다.

### 기본 임계치
- `MIN_WIN_RATE`: 0.55
- `MIN_AVG_ROI`: 0.002
- `MIN_SHARPE`: 1.0
- `MAX_MDD`: 0.10
- `MIN_ENTRIES`: 50
- `TOP_N`: 10

이 값들은 `f5_ml_pipeline/10_select_best_strategies.py`를 편집하여 자유롭게 조정할 수 있습니다.
