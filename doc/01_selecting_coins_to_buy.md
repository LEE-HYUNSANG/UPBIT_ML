# 매수 대상 코인 선정 로직

이 문서는 시스템이 어떤 방식으로 매수 후보 코인을 결정하는지 설명합니다. 초보 기획자가 읽기 쉽도록 핵심 역할과 관련 파일, 주요 함수, 동작 순서를 순서대로 정리했습니다.

## 역할
- F1 모듈은 **모니터링 목록**을 관리하여 F2와 F3 모듈이 처리할 코인을 한정합니다.
- F5 모듈에서 추천한 코인을 우선 사용하며 없을 경우 기존 캐시를 활용합니다.

## 사용되는 관련 파일
| 경로 | 설명 |
| --- | --- |
| `f1_universe/universe_selector.py` | 유니버스(매매 대상 코인) 선택 로직의 대부분이 구현되어 있습니다. |
| `config/f5_f1_monitoring_list.json` | 웹 대시보드나 ML 파이프라인에서 지정한 모니터링 코인 목록입니다. |
| `f5_ml_pipeline/ml_data/10_selected/selected_strategies.json` | ML 백테스트 결과 중 선별된 코인 목록입니다. |
| `config/current_universe.json` | 최근에 선택된 코인 목록이 저장됩니다. |
| `logs/F1_signal_engine.log` | 유니버스 결정 과정의 로그가 기록됩니다. |

## 사용되는 함수
- `load_monitoring_coins()` – 모니터링 파일을 읽어 코인 리스트를 반환합니다. 【F:f1_universe/universe_selector.py†L47-L67】
- `load_selected_universe()` – ML 파이프라인이 남긴 코인 목록을 불러옵니다. 【F:f1_universe/universe_selector.py†L137-L156】
- `select_universe()` – 위 두 목록을 차례로 확인하여 최종 유니버스를 결정합니다. 【F:f1_universe/universe_selector.py†L116-L132】
- `update_universe()` – 결정된 유니버스를 메모리와 `current_universe.json`에 저장합니다. 【F:f1_universe/universe_selector.py†L133-L151】
- `schedule_universe_updates()` – 일정 주기로 `update_universe()`를 실행하는 백그라운드 스레드를 시작합니다. 【F:f1_universe/universe_selector.py†L200-L215】

## 동작 흐름
1. **전략 선별** – F5 파이프라인의 `10_select_best_strategies.py`가 우수 코인을 `f5_f1_monitoring_list.json`에 기록합니다.
2. **유니버스 선택** – `select_universe()`가 모니터링 목록 → ML 추천 목록 → 기존 캐시 순으로 조회하여 리스트를 결정합니다.
3. **파일 갱신** – `update_universe()`가 선택된 코인을 `current_universe.json`에 저장하고 로그에 남깁니다.
4. **주기적 갱신** – `schedule_universe_updates()`가 30분 간격(기본값)으로 위 절차를 반복하여 항상 최신 유니버스를 유지합니다.

## 로그 위치 및 설명
- 주요 활동은 `logs/F1_signal_engine.log` 파일에 남습니다. 유니버스가 변경되면 "Universe updated" 메시지가 기록되어 추적할 수 있습니다.
