# UPBIT AutoTrader HS

This project contains utilities for building a trading universe and evaluating trading signals.

## Universe cache

The latest selected trading universe is saved to `config/current_universe.json`. It is written by `f1_universe.universe_selector.update_universe()` and loaded on startup via `load_universe_from_file()`.

External processes such as `signal_loop.py` can use this file to share the same universe.

## Orderbook batching

`f1_universe.universe_selector.apply_filters` fetches orderbook data in batches of up to 100 tickers with a single API call per chunk. This reduces the number of requests sent to Upbit when building the universe.

## Running `signal_loop.py`

To start the F1/F2 signal loop, run:

```bash
python signal_loop.py
```

Logs are written to `logs/F1F2_loop.log`.


## Credentials

The application requires Upbit API keys and a Telegram bot token to operate.
Credentials are loaded using `f3_order.utils.load_env()`. This function first
checks the operating system's environment variables and then looks for a
`.env.json` file if present.

To keep your secrets out of version control, create an untracked `.env.json`
file or set the following environment variables:

```json
{
  "UPBIT_KEY": "<your key>",
  "UPBIT_SECRET": "<your secret>",
  "TELEGRAM_TOKEN": "<telegram token>",
  "TELEGRAM_CHAT_ID": "<chat id>"
}
```

Place the file next to `app.py` and ensure it is ignored by Git using
`.gitignore`.


## F4 Risk Manager Guide

The F4 module monitors drawdowns, daily loss and execution errors. It operates as a finite state machine with the following states:

- **ACTIVE** – normal trading allowed.
- **PAUSE** – new entries are blocked for a configurable time period.
- **HALT** – all positions are liquidated and trading stops until manually restarted.

`pause()`, `halt()` and `disable_symbol()` automatically close relevant open positions using the order engine and send a Telegram alert through `ExceptionHandler.send_alert()`.
Risk events are recorded in `logs/risk_events.db` for later review.

When the risk configuration file is modified (e.g. `config/setting_date/Latest_config.json`) the manager detects the change via `hot_reload()` and applies the new parameters immediately. A notification is also sent.

To recover from a halted state simply restart the application or wait for `periodic()` to transition back to `ACTIVE` when allowed.
