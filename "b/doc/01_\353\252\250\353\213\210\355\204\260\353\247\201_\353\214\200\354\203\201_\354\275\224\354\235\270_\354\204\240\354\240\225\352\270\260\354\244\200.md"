# 모니터링 대상 코인 선정기준

이 문서는 F1 모듈에서 **모니터링 대상 코인(유니버스)** 을 구성하는 방법을 설명합니다. 초보 기획자도 이해하기 쉽도록 주요 함수와 변수의 역할을 정리했습니다.

## 주요 파일과 위치

- `f1_universe/universe_selector.py` – 코인 필터링 로직과 유니버스 관리 함수가 정의되어 있습니다.
- `config/universe.json` – 필터 기준이 저장된 설정 파일입니다.
- `config/current_universe.json` – 최종 선정된 티커 목록이 저장되는 캐시 파일입니다.
- `f5_ml_pipeline/ml_data/10_selected/selected_strategies.json` – ML 파이프라인에서 선별된 전략 목록이 있을 경우 이 파일에 있는 `symbol` 값이 우선 적용됩니다.

## 필터 기준 변수

`config/universe.json` 예시와 각 항목의 의미는 다음과 같습니다.

```json
{
  "min_price": 700.0,
  "max_price": 23000.0,
  "min_volatility": 1.5,
  "min_ticks": 0,
  "max_spread": 0.15,
  "volume_rank": 30,
  "universe_size": 0
}
```

- **min_price, max_price** – 24시간 내 거래 가격 범위입니다. 이 구간에 포함되지 않으면 제외됩니다.
- **min_volatility** – 당일 고가와 저가 차이를 기준으로 한 변동성(%) 최소값입니다.
- **min_ticks** – 고가와 저가의 차이를 호가 단위로 환산한 최소 값입니다.
- **max_spread** – 매도호가 1호와 매수호가 1호 사이의 괴리(%) 허용 한도입니다.
- **volume_rank** – 24시간 거래대금 기준 상위 몇 종목을 후보로 삼을지 결정합니다.
- **universe_size** – 필터 통과 후 최종 몇 종목을 사용할지 정합니다. 0이면 전부 사용합니다.

## 핵심 함수 요약

아래 함수들은 `f1_universe.universe_selector` 모듈에 위치합니다.

### `load_config(path=CONFIG_PATH)`

`config/universe.json` 파일을 읽어 필터 기준을 딕셔너리로 반환합니다. 파일이 없으면 기본값을 제공합니다.

### `get_top_volume_tickers(size=50)`

Upbit API의 24시간 거래대금 정보를 바탕으로 상위 `size`개 티커 목록을 반환합니다. 기본값은 50개입니다.

### `apply_filters(tickers, config)`

`tickers` 목록에 대해 위에서 설명한 가격, 변동성, 스프레드 등의 조건을 적용하고 통과한 티커만 반환합니다.

### `select_universe(config=None)`

1. `get_top_volume_tickers(volume_rank)`로 후보 종목을 가져옵니다.
2. `apply_filters`로 필터를 거친 뒤 필요한 경우 `universe_size`만큼 잘라 최종 리스트를 만듭니다.
3. 결과를 로그에 남기고 반환합니다.

### `update_universe(config=None)`

`select_universe`로 얻은 티커를 내부 캐시에 저장하고 `config/current_universe.json` 파일을 갱신합니다.

### `load_selected_universe(path=SELECTED_STRATEGIES_FILE)`

ML 파이프라인에서 선택된 전략 파일을 읽어 `symbol` 목록을 반환합니다. 이 값이 존재하면 기본 유니버스보다 우선적으로 사용됩니다.

### `load_universe_from_file(path=UNIVERSE_FILE)`

캐시 파일(`current_universe.json`)을 불러와 전역 리스트에 적재합니다.

### `get_universe()`

1. 먼저 `load_selected_universe` 결과가 있으면 그것을 반환합니다.
2. 없다면 현재 캐시된 유니버스를 반환하거나, 캐시가 비어 있으면 파일에서 로드합니다.

### `schedule_universe_updates(interval=1800, config=None)`

백그라운드 스레드에서 일정 간격(`interval` 초, 기본 30분)으로 `update_universe`를 실행해 유니버스를 갱신합니다.

### `init_coin_positions(threshold=5000.0, path=POSITIONS_FILE)`

보유 중인 자산을 조회해 평가금액이 `threshold` 이상이면 `config/coin_positions.json`에 등록합니다. 이미 열려 있는 포지션은 중복 등록하지 않습니다.

## 동작 흐름

1. 어플리케이션 시작 시 `load_config()`로 필터 설정을 읽습니다.
2. `load_universe_from_file()`을 통해 기존 캐시를 메모리로 불러옵니다.
3. `schedule_universe_updates()`를 호출하여 일정 주기로 `update_universe()`가 실행되게 합니다.
4. `get_universe()`를 호출하면 현재 메모리에 있는 유니버스 또는 ML 결과 파일의 티커 목록을 사용할 수 있습니다.

위 과정을 통해 신호 계산 모듈(`signal_loop.py`)이나 웹 대시보드(`app.py`)에서 항상 최신 기준의 모니터링 대상 코인을 활용할 수 있습니다.

