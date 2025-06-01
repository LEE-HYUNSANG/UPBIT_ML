# Telegram Notifications

The system can send various notifications through Telegram. Each notification
category is toggled in `f6_setting/01_alarm_control/alarm_config.json`.
Messages are delivered by `ExceptionHandler.send_alert` when both
`TELEGRAM_TOKEN` and `TELEGRAM_CHAT_ID` are configured.

Supported categories:

- **system_start_stop** – server start/stop messages.
- **buy_monitoring** – updates from the buy monitoring page.
  A notification is also sent when a new buy signal is generated.
- **order_execution** – buy and sell executions.
- **system_alert** – warnings from the risk manager or KPI guard.
- **ml_pipeline** – machine learning pipeline status.

Default templates for order alerts reside in the same configuration file and can
be customized.

The web UI under **환경설정** now exposes these options. The page loads values
from `/api/alarm_config` and posts changes back to the same endpoint when the
user clicks the Save button.
