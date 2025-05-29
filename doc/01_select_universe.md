# 모니터링 대상 코인 선정 기준

이 문서는 F1 모듈에서 **모니터링 대상 코인(유니버스)** 을 어떻게 선정하는지 설명합니다. 초보 기획자도 이해하기 쉽도록 주요 파일과 함수만 간단히 정리했습니다.

## 주요 파일

- `f1_universe/universe_selector.py` – 유니버스 관리 함수가 모여 있습니다.
- `f5_ml_pipeline/ml_data/10_selected/selected_strategies.json` – ML 파이프라인이 뽑아낸 전략 목록. 여기 있는 `symbol` 값만 사용합니다.
- `config/current_universe.json` – 최종 선정된 티커 목록을 저장하는 캐시 파일입니다.

### `selected_strategies.json` 예시

```json
[
  {
    "symbol": "KRW-BTC",
    "win_rate": 0.61,
    "avg_roi": 0.0032,
    "sharpe": 1.45,
    "max_drawdown": 0.07,
    "total_entries": 85,
    "params": {"lookback": 20, "stop_loss": 0.05}
  },
  {"symbol": "KRW-ETH"}
]
```

이 파일에서 `symbol` 값만 뽑아 `["KRW-BTC", "KRW-ETH"]` 형태로 사용합니다.

## 핵심 함수 요약

### `load_selected_universe(path=SELECTED_STRATEGIES_FILE)`
`selected_strategies.json` 파일을 읽어 티커 배열을 반환합니다.

### `select_universe(config=None)`
1. `load_selected_universe` 결과가 있으면 그대로 반환합니다.
2. 없으면 `load_universe_from_file` 로 `current_universe.json` 캐시를 불러옵니다.

### `update_universe(config=None)`
`select_universe` 결과를 메모리와 캐시에 저장합니다.

### `get_universe()`
`load_selected_universe`가 우선이며, 비어 있으면 현재 메모리 또는 캐시에서 가져옵니다.

### `init_coin_positions(threshold=5000.0, path=POSITIONS_FILE)`
보유 자산을 조회해 평가금액이 `threshold` 이상이면 `config/coin_positions.json`에 등록합니다.

위 과정을 통해 신호 계산 모듈(`signal_loop.py`)이나 웹 대시보드(`app.py`)에서 항상 최신 모니터링 대상을 활용할 수 있습니다.
