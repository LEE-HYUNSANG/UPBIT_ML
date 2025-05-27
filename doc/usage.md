# Usage

1. Install dependencies using `pip install -r requirements.txt`.
2. Provide Upbit API credentials and a Telegram bot token via environment
   variables or an `.env.json` file:
   ```json
   {
     "UPBIT_KEY": "<your key>",
     "UPBIT_SECRET": "<your secret>",
     "TELEGRAM_TOKEN": "<telegram token>",
     "TELEGRAM_CHAT_ID": "<chat id>"
   }
   ```
3. Run the main loop:
   ```bash
   python signal_loop.py
   ```
   Logs are written to `logs/` and rotate automatically.
4. Optional: start `app.py` to access the dashboard and REST APIs.
