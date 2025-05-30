# 유니버스 결정 절차

이 문서는 F1 모듈이 어떤 방식으로 매매 대상 코인 목록(유니버스)을
결정하는지 단계별로 설명합니다. 초보 기획자가 읽어도 이해할 수 있도록
관련 파일과 동작 흐름을 간단하게 정리했습니다.

## 핵심 역할

- **모니터링 대상**을 정해 F2/F3가 실시간으로 다룰 코인을 제한합니다.
- **데이터 수집 대상**을 정해 F5 머신러닝 학습을 위한 데이터를 모읍니다.

주요 코드는 `f1_universe/universe_selector.py`에 있으며 주기적으로
`config/current_universe.json`에 결과를 저장합니다.

## 사용되는 파일

| 파일 | 설명 |
| ---- | ---- |
| `config/coin_list_monitoring.json` | 실전 모니터링에 사용할 코인 목록. 빈 배열이면 다른 데이터로 대체됩니다. |
| `f5_ml_pipeline/ml_data/10_selected/selected_strategies.json` | 백테스트에서 선별된 코인 목록 |
| `config/universe.json` | 가격, 거래량 등 기본 필터 조건. |
| `config/coin_list_data_collection.json` | 학습용 데이터를 수집할 코인 목록. |
| `config/filter_coin_data_collection.json` | 데이터 수집 시 적용할 가격·거래량 조건. |
> `coin_list_monitoring.json`이 비어 있으면 위 전략 목록을 우선 사용합니다.
| `config/current_universe.json` | 마지막으로 선택된 유니버스가 기록되는 파일. |

로그는 `logs/F1_signal_engine.log`와 `logs/F1-F2_loop.log`에 저장됩니다.

## 주요 함수

- `load_monitoring_coins()` – 모니터링 목록을 읽어 리스트로 반환합니다.
- `load_selected_universe()` – ML 파이프라인에서 선별한 목록을 읽어옵니다.
- `select_universe()` – 위 두 목록을 순서대로 확인한 뒤 없으면
  `load_universe_from_file()` 결과를 사용합니다.
- `update_universe()` – 선택된 유니버스를 메모리와 `current_universe.json`에 갱신합니다.
- `schedule_universe_updates()` – 주기적으로 `update_universe()`를 호출하는 백그라운드 스레드를 시작합니다.

## 동작 흐름

1. **전략 선별(F5 모듈)**
   - `f5_ml_pipeline/10_select_best_strategies.py`가 백테스트 결과를 평가하여
     좋은 심볼을 `config/coin_list_monitoring.json`에 저장합니다.
2. **유니버스 로드**
   - `signal_loop.py` 실행 시 `schedule_universe_updates()`가 동작하여
     30분마다 `select_universe()`를 호출합니다.
   - `select_universe()`는 `coin_list_monitoring.json` → `selected_strategies.json`
     → `current_universe.json` 순으로 확인해 첫 번째로 발견된 리스트를 사용합니다.
3. **파일 갱신**
   - 결정된 유니버스는 `config/current_universe.json`에 기록되어
     다른 모듈이 동일한 목록을 참조할 수 있게 합니다.
4. **데이터 수집**
   - 별도로 실행되는 `f5_ml_pipeline/01_data_collect.py`는
     `coin_list_data_collection.json`과 `filter_coin_data_collection.json`을 읽어
     학습용 데이터를 수집합니다.

이 구조를 통해 모니터링 대상과 학습용 대상이 분리되며,
웹 대시보드나 ML 파이프라인 결과에 따라 유니버스가 자동으로 업데이트됩니다.
