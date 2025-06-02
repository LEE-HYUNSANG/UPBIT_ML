# Telegram Notifications

The system can send various notifications through Telegram. Each notification
category is toggled in `f6_setting/01_alarm_control/alarm_config.json`.
Messages are delivered by `ExceptionHandler.send_alert` when both
`TELEGRAM_TOKEN` and `TELEGRAM_CHAT_ID` are configured.

Supported categories:

- **system_start_stop** – server start/stop messages.
- **buy_monitoring** – updates from the buy monitoring page.
  A notification is also sent when a new buy signal is generated.
- **order_execution** – buy and sell executions. A notification is also sent
  when a sell order is attempted.
- **system_alert** – warnings from the risk manager or KPI guard.
- **ml_pipeline** – machine learning pipeline status.

Example ML pipeline messages:

```
[INFO] 머신러닝 학습 시작] at 12:34:56
[INFO] 머신러닝 학습 종료] at 12:45:01 - selected_coinList: CBK, WAVES, CELO
```

Order execution messages use the following format:

```
[INFO] 매수 시그널] WAVES @1000.0
[INFO] 매수 주문 성공] WAVES 매수 금액: 10,000원 @1000.0
[INFO] 매도 완료] WAVES 매도 금액: 10,500원 @1050.0 이익:+500원
```

Default templates for order alerts reside in the same configuration file and can
be customized. The sell template now includes a `{reason}` placeholder which is
automatically filled with "익절 매도" or "손절 매도" based on the exit type.

The web UI under **환경설정** now exposes these options. The page loads values
from `/api/alarm_config` and posts changes back to the same endpoint when the
user clicks the Save button.
