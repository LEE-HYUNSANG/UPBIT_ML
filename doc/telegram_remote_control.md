# Telegram Remote Control

`f6_setting.remote_control` provides a small Telegram bot to start and stop the
trading loop remotely. It relies on the `pyTelegramBotAPI` package.

1. Create a bot with `@BotFather` and note the token.
2. Set the `TELEGRAM_TOKEN` environment variable with the token.
3. Run `f6_setting.remote_control.start_bot()` to begin polling.

Use `/on` or `/off` in the chat. The bot writes `server_status.txt` with `ON` or
`OFF` next to `remote_control.py` by default. `signal_loop.main_loop` reads this
file each cycle and only operates when the status is `ON`. Set the
`SERVER_STATUS_FILE` environment variable to change the path.
