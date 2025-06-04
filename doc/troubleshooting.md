# 주문 실행 문제 해결

이 문서는 `f2_ml_buy_signal.run()` 실행 이후 `config/f2_f2_realtime_buy_list.json`이 갱신되었는데도
주문이 이루어지지 않을 때 확인할 항목을 정리합니다. 각 단계별 로그 확인 방법과 단위 테스트
실행 방법을 함께 소개합니다.

## 기본 흐름
1. `f2_ml_buy_signal/02_ml_buy_signal.py`의 `run()` 함수가 모니터링 중인 코인을 순회하며
    매수 신호를 계산하고 결과를 `config/f2_f2_realtime_buy_list.json`에 저장합니다.
2. `app.py`의 `start_buy_signal_scheduler()`가 15초마다 위 파일을 읽어
    `buy_list_executor.execute_buy_list()`를 호출합니다.
3. `buy_list_executor.execute_buy_list()`는 매수 가능한 항목을 필터링한 뒤 현재 가격을 조회하고
    `OrderExecutor.entry()`로 전달합니다.
4. `OrderExecutor.entry()`는 주문을 전송하고 `PositionManager`를 통해 포지션을 기록합니다.
5. 주문이 체결되면 `logs/f3/F3_position_manager.log`와 `logs/etc/events.jsonl`에 결과가 남습니다.

## 단계별 점검
- **1단계: 매수 목록 생성 확인**

    `logs/f2/f2_ml_buy_signal.log`에서 `saved buy_list=` 라인을 찾습니다.

    ```text
    2025-06-04 08:05:30,942 [F2] [INFO] [RUN] saved buy_list=[{'symbol': 'KRW-TRUMP', ...}]
    ```

    위 로그가 없으면 `run()` 자체가 실행되지 않았거나 중간에 오류가 발생한 것입니다.

- **2단계: 스케줄러 동작 여부**

`app.py`를 실행하면 스케줄러 스레드가 생성되어 15초마다 실행됩니다.
`logs/etc/web.log`에서 다음과 같은 메시지를 확인합니다.

    ```text
    INFO schedule buy_list_executor.execute_buy_list
    ```

이 로그가 없다면 스케줄러가 시작되지 않은 상태입니다.  
추가로 예외가 발생하면 같은 파일에 ``buy signal error`` 라인이
스택 트레이스와 함께 기록됩니다. 이를 통해 어느 단계에서 문제가
생겼는지 확인할 수 있습니다.

- **3단계: 매수 실행 과정**

    `logs/f2/buy_list_executor.log`에 `Targets:`와 `Executed buys:`가 기록됩니다.

    ```text
    2025-06-04 08:05:31,019 [F2] [F3] Ticker prices: {'KRW-CBK': 712.7}
    2025-06-04 08:05:31,020 [F2] [F3] Executing buy for KRW-CBK at 712.7
    ```

    여기서 계속 `No buy candidates found`만 나타난다면 JSON 파일의 `buy_count` 값이 1로 바뀌었거나
    `pending` 플래그가 1로 남아 있는지 확인합니다.

- **4단계: 주문 처리 결과 확인**

    `logs/f3/F3_order_executor.log`에서 주문 성공 또는 실패 로그를 찾을 수 있습니다.

    성공 예시:

    ```text
    Filled KRW-CBK 10.0 at 712.7
    ```

    실패 예시:

    ```text
    ERROR PermissionError [Errno 13] config/f2_f2_realtime_buy_list.json
    ```

    권한 오류가 발생하면 해당 파일의 읽기/쓰기 권한을 점검합니다.

- **5단계: 포지션 관리 및 매도**

    포지션이 열리면 `logs/f3/F3_position_manager.log`에 다음과 같이 남습니다.

    ```text
    open_position KRW-CBK qty=10 price=712.7
    ```

    이후 손절이나 익절 등 매도 주문이 실행될 때도 동일한 파일에 기록됩니다.

## 자주 발생하는 예외 사례
- **PermissionError**: `logs/f3/F3_exception_handler.log` 또는 `web.log`에 경로와 함께
  기록됩니다. 윈도우 환경에서 `unlock error` 메시지가 반복된다면 최신 버전에서 수정된
  버그이므로 코드를 업데이트하세요. 잠금 해제 전 파일 포인터를 0으로 되돌리도록
  개선되었습니다.
- **잔고 부족**: `F3_order_executor.log`에 `insufficient funds` 메시지가 표시됩니다.
- **네트워크 오류**: Upbit API 호출 실패 시 `web.log`에 HTTP 오류 코드가 남습니다.

각 예외 메시지를 확인한 뒤 설정 파일과 네트워크 상태를 점검하세요.

## 단위 테스트 실행 방법
모든 테스트를 실행하려면 프로젝트 루트에서 다음 명령을 실행합니다.

```bash
pytest -q
```

특정 모듈만 확인하고 싶을 때는 `-k` 옵션을 사용합니다.

```bash
# buy_list_executor 동작만 테스트
pytest -k test_buy_list_executor -q

# 주문 관리 로직 테스트
pytest tests/test_order_manager.py::TestOrderManager -q
```

테스트는 가상 주문을 사용하므로 실계좌 주문이 실행되지 않습니다. 모든 테스트가 통과하는지
확인하여 코드 변경이 기존 기능에 영향을 주지 않는지 점검하세요.
