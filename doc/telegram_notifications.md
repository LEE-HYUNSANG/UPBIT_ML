# Telegram Notifications

The system can send brief trade alerts via Telegram when a buy or sell order is executed.
Messages are delivered by `ExceptionHandler.send_alert` if both `TELEGRAM_TOKEN` and
`TELEGRAM_CHAT_ID` are configured in `.env.json` or the environment.

- **Buy alerts** – triggered from `OrderExecutor.entry` after a filled order.
- **Sell alerts** – triggered whenever `PositionManager.execute_sell` closes part
  or all of a position.

These notifications help keep track of trading activity without constantly
monitoring the dashboard.
