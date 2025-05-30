# 코인 매수 모니터링 로직

이 문서는 F2 모듈에서 매수 신호를 감지하고 F3 모듈에서 실제 매수 주문을 실행하는 과정을 설명합니다. 코드 흐름과 사용되는 주요 함수, 변수들을 초보 기획자도 이해하기 쉽게 정리했습니다.

## 관련 파일
- `f2_signal/signal_engine.py` – 매수/매도 조건 계산 함수 `f2_signal` 정의
- `f3_order/order_executor.py` – 신호를 받아 주문을 처리하는 `OrderExecutor` 클래스
- `f3_order/smart_buy.py` – 시장가와 IOC 주문을 조합한 `smart_buy` 함수
- `f3_order/position_manager.py` – 포지션 정보를 저장하고 갱신하는 `PositionManager`

## 주요 함수와 변수

### `f2_signal(df_1m, df_5m, symbol="", trades=None, calc_buy=True, calc_sell=True, strategy_codes=None)`
`f2_signal`은 머신러닝 모델을 이용해 1분 봉 데이터에서 매수 신호를 계산합니다. 기존의 전략 공식은 사용하지 않으며 반환 값의 형식은 다음과 같습니다.
```python
{
    "symbol": symbol,
    "buy_signal": bool,    # 매수 가능 여부
    "sell_signal": bool,   # 매도 가능 여부
    "buy_triggers": [],
    "sell_triggers": []
}
```
매수 조건이 충족되면 `buy_signal`이 `True`가 됩니다. 별도의 `f2_ml_buy_signal.run()` 함수가 `coin_list_monitoring.json`에 있는 종목을 순회하면서 이 값을 확인하고, `config/coin_realtime_buy_list.json`에 매수 대상 코인을 기록합니다.【F:f2_ml_buy_signal/f2_ml_buy_signal.py†L117-L135】


### `OrderExecutor.entry(signal)`
`OrderExecutor.entry`는 위 결과를 받아 실제 매수 주문을 수행합니다. RiskManager에서 특정 심볼이 차단되었는지 확인한 후 `smart_buy`를 호출하여 주문을 시도합니다. 체결되면 `PositionManager.open_position`으로 포지션이 저장됩니다.
【F:f3_order/order_executor.py†L48-L96】

### `smart_buy(signal, config, dynamic_params, position_manager, parent_logger=None)`
`smart_buy`는 스프레드가 넓을 경우 IOC 주문을 우선 시도하고 실패 시 시장가 주문으로 넘어갑니다. 주문 수량은 `config["ENTRY_SIZE_INITIAL"]`을 사용해 계산하며 최소 수량은 0.0001로 제한됩니다.【F:f3_order/smart_buy.py†L20-L53】

### 주요 설정 값
- `ENTRY_SIZE_INITIAL` – 첫 매수 시 투입하는 원화 금액
- `MAX_RETRY` – IOC 주문 재시도 횟수 (기본 2회)
- `SPREAD_TH` – 스프레드 임계값. 이보다 좁으면 바로 시장가 주문

위 값들은 `config/setting_date/Latest_config.json` 또는 기타 설정 파일에서 관리됩니다.【F:config/setting_date/Latest_config.json†L1-L23】
매수 신호 계산 과정과 결과는 `logs/f2_ml_buy_signal.log`에 기록됩니다.
필수 패키지가 없으면 해당 오류 메시지도 이 파일에 남습니다.
최근 업데이트로 실행 시작과 종료, 데이터 수집, 예측 확률 등 세부 정보가 모두 로그에
표시되므로 문제 발생 시 원인을 쉽게 추적할 수 있습니다.

## 동작 흐름
1. `signal_loop.py`의 `process_symbol`에서 각 심볼의 OHLCV 데이터를 받아 `f2_signal`을 호출합니다.
2. 반환된 딕셔너리에서 `buy_signal`이 `True`이면 `OrderExecutor.entry`가 실행됩니다.
3. `entry` 내부에서 동일 심볼의 기존 포지션을 확인하고, 없을 경우 `smart_buy`로 주문을 시도합니다.
4. 주문이 체결되면 `PositionManager.open_position`을 통해 포지션 목록에 추가되고, 텔레그램 알림이 전송됩니다.

이 과정을 통해 시스템은 지속적으로 코인을 모니터링하며 매수 조건이 충족될 때 자동으로 주문을 실행합니다.
