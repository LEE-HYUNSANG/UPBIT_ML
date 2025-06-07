# 주문 실행 문제 해결

이 문서는 `f2_buy_signal.run()` 실행 이후 `config/f2_f2_realtime_buy_list.json`이 갱신되었는데도
주문이 이루어지지 않을 때 확인할 항목을 정리합니다. 각 단계별 로그 확인 방법과 단위 테스트
실행 방법을 함께 소개합니다.

## 기본 흐름
1. `f2_buy_signal/02_ml_buy_signal.py`의 `run()` 함수가 모니터링 중인 코인을 순회하며
    매수 신호를 계산하고 결과를 `config/f2_f2_realtime_buy_list.json`에 저장합니다.
2. `app.py`에서 F5 예측 결과가 생성될 때마다 해당 파일을 읽어
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

`app.py`를 실행하면 스케줄러 스레드가 생성되어 F5 예측 결과가 업데이트될 때마다 실행됩니다.
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
    최신 버전에서는 함수 시작 시 `execute_buy_list start` 로그가 먼저
    남으므로, 해당 메시지가 없으면 스케줄러 호출 자체가 실패한
    상황으로 볼 수 있습니다.

    ```text
    2025-06-04 08:05:31,019 [F2] [F3] Ticker prices: {'KRW-CBK': 712.7}
    2025-06-04 08:05:31,020 [F2] [F3] Executing buy for KRW-CBK at 712.7
    ```

    여기서 계속 `No buy candidates found`만 나타난다면 JSON 파일의 `buy_count` 값이 1로 바뀌었거나
    `pending` 플래그가 1로 남아 있는지 확인합니다.

    최신 버전의 실행기는 주문 전마다 `f6_buy_settings.json`을 다시 읽어 들입니다.
    설정을 변경한 뒤에는 별도 재시작 없이 곧바로 적용됩니다.

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
  스케줄러가 buy list 파일을 잠근 채 주문을 실행하면 중첩 잠금 때문에 같은 오류가
  발생할 수 있습니다. 최신 코드에서는 주문 전 잠금을 해제한 뒤 완료 후 다시 저장하여
  문제를 해결했습니다.
- 파일 잠금이 계속 실패한다면 환경 변수 `UPBIT_DISABLE_LOCKS=1`을 설정해 잠금을
  우회할 수 있습니다. 단, 동시 실행 중인 다른 프로세스가 파일을 수정할 수 있으므로
  일시적인 진단 목적으로만 사용하세요.
- **잔고 부족**: `F3_order_executor.log`에 `insufficient funds` 메시지가 표시됩니다.
  최신 버전에서는 잔고가 없으면 포지션을 자동으로 닫아 반복 주문을 멈춥니다.
- **네트워크 오류**: Upbit API 호출 실패 시 `web.log`에 HTTP 오류 코드가 남습니다.
- **Telegram 알림 누락**: `logs/f3/F3_exception_handler.log`에
  `Telegram credentials missing` 또는 `Alert category disabled`가
  기록되면 토큰이나 설정을 확인하세요.
  전송 시도 후에는 `Telegram sent:` 또는 `Telegram send failed:` 라인이
  같은 파일에 기록됩니다.
- **주문 취소 반복**: 호가가 빠르게 변해 한도 주문이 자주 취소된다면
  `FALLBACK_MARKET` 설정을 `true`로 바꿔 첫 주문이 실패할 때 시장가로
  재시도할 수 있습니다.
- **TypeError: Cannot instantiate typing.Any**: Pandas가 설치되지 않았거나
  구버전 코드에서 빈 데이터프레임을 생성할 때 발생합니다. `pip install -U pandas`
  명령으로 패키지를 설치하거나 최신 코드를 사용하세요.
- **상장폐지 코인**: `F3_position_manager.log`에 `Code not found` 오류가 반복되면
  해당 심볼이 자동으로 포지션 목록에서 제거됩니다.
- **중복 모듈 로드**: 여러 스레드에서 `app.py`의 헬퍼 `_import_from_path()`를
  사용해 모듈을 불러오면 새 인스턴스가 생성되어 상태가 공유되지 않을 수 있습니다.
  최신 버전에서는 이 함수가 `sys.modules`에 모듈을 등록하므로 동일한 이름을
  쓰면 항상 같은 객체가 반환됩니다.

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
