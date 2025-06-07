# 코인 매수 시그널 생성 로직

본 문서는 `01_selecting_coins_to_buy.md`에서 선정된 코인을 대상으로 `f2_buy_signal.check_signals()` 함수가 어떻게 사용되는지 설명합니다.

## 역할
- F2 모듈은 F5 단계의 예측 CSV를 읽어 세 가지 조건을 평가합니다.
- 세 신호가 모두 참일 때만 실매수 대상으로 간주합니다.

## 사용되는 관련 파일
| 경로 | 설명 |
| --- | --- |
| `f2_buy_signal/02_ml_buy_signal.py` | 전체 파이프라인과 실시간 예측 로직을 포함합니다. |
| `f2_buy_signal/01_buy_indicator.py` | EMA와 RSI 기반의 기본 필터 함수를 제공합니다. |
| `config/f5_f1_monitoring_list.json` | 매수 신호를 계산할 코인 목록입니다. |
| `config/f2_f2_realtime_buy_list.json` | 계산된 매수 신호가 저장되는 파일입니다. |
| `logs/f2/f2_ml_buy_signal.log` | 매수 신호 계산 과정의 로그가 기록됩니다. |

## 사용되는 함수
- `run_if_monitoring_list_exists()` – 모니터링 목록이 존재할 때만 `run()`을 호출합니다. 【F:f2_ml_buy_signal/02_ml_buy_signal.py†L361-L371】
- `f2_buy_signal.run()` – 각 코인에 대해 `check_buy_signal()`을 호출하고 결과를 JSON 파일에 기록합니다. 【F:f2_ml_buy_signal/02_ml_buy_signal.py†L322-L359】
- `check_buy_signal()` – 모델 예측 값과 지표 조건을 확인하여 `(buy, rsi_flag, trend_flag)`를 반환합니다. 【F:f2_ml_buy_signal/02_ml_buy_signal.py†L256-L303】

## 동작 흐름
1. `signal_loop.process_symbol()`이 주기적으로 `check_signals(symbol)`을 호출합니다.
2. 반환된 세 신호가 모두 `True`이면 해당 코인이 실시간 매수 리스트에 기록됩니다.
3. 로그 파일에서 각 심볼의 예측 값과 최종 판단 여부를 확인할 수 있습니다.
