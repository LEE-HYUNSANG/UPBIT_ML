# Telegram Remote Control

`f6_setting.telegram_control` provides a small Telegram bot to start and stop the
trading loop remotely. It relies on the `pyTelegramBotAPI` package.

1. Create a bot with `@BotFather` and note the token.
2. Set the `TELEGRAM_TOKEN` environment variable with the token.
3. Run `f6_setting.telegram_control.start_bot()` to begin polling.

Use `/on` or `/off` in the chat. The bot writes `server_status.txt` with `ON` or
`OFF`. `signal_loop.main_loop` reads this file each cycle and only operates when
the status is `ON`.
