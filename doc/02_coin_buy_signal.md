# 코인 매수 시그널 생성 로직

본 문서는 `01_selecting_coins_to_buy.md`에서 선정된 코인을 대상으로 `f2_buy_signal.check_signals()` 함수가 어떻게 사용되는지 설명합니다.

## 역할
- F2 모듈은 F5 단계의 예측 CSV를 읽어 세 가지 조건을 평가합니다.
- 세 신호가 모두 참일 때만 실매수 대상으로 간주합니다.

## 사용되는 관련 파일
| 경로 | 설명 |
| --- | --- |
| `f2_buy_signal/__init__.py` | `check_signals()` 함수 구현 |
| `f5_ml_pipeline/ml_data/08_pred/` | 예측 결과 CSV 저장 위치 |
| `config/f2_f2_realtime_buy_list.json` | 계산된 매수 신호가 저장되는 파일 |
| `logs/f2/f2_buy_signal.log` | 매수 신호 계산 로그 |

## 동작 흐름
1. `signal_loop.process_symbol()`이 주기적으로 `check_signals(symbol)`을 호출합니다.
2. 반환된 세 신호가 모두 `True`이면 해당 코인이 실시간 매수 리스트에 기록됩니다.
3. 로그 파일에서 각 심볼의 예측 값과 최종 판단 여부를 확인할 수 있습니다.
