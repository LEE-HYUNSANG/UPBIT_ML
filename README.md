# UPBIT AutoTrader HS

This project contains utilities for building a trading universe and evaluating trading signals.

## Overview
This project consists of four main components:
- **F1 Universe Selector** gathers tradable tickers.
- **F2 Signal Engine** analyzes OHLCV data and issues buy/sell signals.
- **F3 Order Executor** manages orders and open positions.
- **F4 Risk Manager** monitors drawdowns and can pause or halt trading.

See the [doc](doc/) folder for more details.
## Installation
Install the required Python packages with:

```bash
pip install -r requirements.txt
```

This installs dependencies such as `pandas` and `scikit-learn` that are needed
for the ML buy signal script.

This ensures modules such as `tqdm` are available when running the pipeline scripts.
The file also includes machine learning dependencies (`optuna`, `lightgbm` and
`scikit-learn`) required for `f5_ml_pipeline/06_optuna_tpe.py`.
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

Logs are written to `logs/F1-F2_loop.log`.
Each log file automatically rotates when it exceeds 100&nbsp;MB. Previous files
are numbered sequentially as `*.1`, `*.2`, and so on.
To run the standalone ML buy signal routine execute the module from the project
root:
```bash
python -m f2_ml_buy_signal.02_ml_buy_signal
```
Results are logged to `logs/f2_ml_buy_signal.log`. If a required package is
missing the error is also written to this log file.
The `run()` function updates `config/f2_f2_realtime_buy_list.json`.
The Flask scheduler automatically calls
`buy_list_executor.execute_buy_list()` after each run so any buy candidates are
immediately ordered. You can still invoke this function manually if needed.


## Running the order executor

For quick testing you may execute the order module directly:

```bash
python f3_order/order_executor.py
```

When run this way the script prepends the project root to `sys.path` so the
relative imports work. The recommended invocation in production is:

```bash
python -m f3_order.order_executor
```

Both methods start the default `OrderExecutor` instance which logs activity to
`logs/F3_order_executor.log`.

## Running the web dashboard

Launch the Flask application with:

```bash
python app.py
```

The server listens on port 3000 so you can visit `http://localhost:3000` in your browser.

When the server starts three background tasks are launched:

- `f5_ml_pipeline/01_data_collect.py` continuously fetches 1‑minute OHLCV data.
- `f2_ml_buy_signal/02_ml_buy_signal.py` runs after each minute candle to update the real‑time buy list.
- `f5_ml_pipeline/run_pipeline.py` executes every five minutes to retrain and evaluate models.


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

Any issues loading credentials are recorded in `logs/F3_utils.log`.

When credentials are set, brief buy/sell notifications are sent through
Telegram whenever orders are executed. See
[doc/telegram_notifications.md](doc/telegram_notifications.md).
Remote start/stop commands are documented in
[doc/telegram_remote_control.md](doc/telegram_remote_control.md).

Startup messages about credential loading are written to `logs/F3_utils.log`.
Check this file if account queries fail to verify that API keys were detected.

## Remote control

The trading loop checks `server_status.txt` each cycle. This file is stored next to `remote_control.py` by default.
When it contains `ON` the loop runs normally. Writing `OFF` stops trading but leaves the program running.
You can edit the file manually or send `/on` and `/off` commands to the Telegram bot which updates the file.
Set `SERVER_STATUS_FILE` to customize the location.

The `/api/auto_trade_status` endpoint now synchronizes this file as well. Using
`POST` to enable or disable trading immediately updates `server_status.txt` so
the main loop reacts without a restart.

See [doc/telegram_remote_control.md](doc/telegram_remote_control.md) for details.



## F4 Risk Manager Guide

The F4 module monitors drawdowns, daily loss and execution errors. It operates as a finite state machine with the following states:

- **ACTIVE** – normal trading allowed.
- **PAUSE** – new entries are blocked for a configurable time period.
- **HALT** – all positions are liquidated and trading stops until manually restarted.

`pause()`, `halt()` and `disable_symbol()` automatically close relevant open positions using the order engine and send a Telegram alert through `ExceptionHandler.send_alert()`.
Risk events are recorded in `logs/risk_events.db` for later review.

When the risk configuration file is modified (e.g. `config/setting_date/f4_f3_latest_config.json`) the manager detects the change via `hot_reload()` and applies the new parameters immediately. A notification is also sent. The `OrderExecutor` mirrors updated trade sizing values such as `ENTRY_SIZE_INITIAL` whenever a reload occurs, so buy quantities stay in sync with the risk settings.

To recover from a halted state simply restart the application or wait for `periodic()` to transition back to `ACTIVE` when allowed.

## Initial balance sync

When the application starts the `PositionManager` now fetches account balances
using the Upbit API. Any holding worth at least 5,000 KRW is registered as an
``imported`` position so that F2/F3 can monitor sell signals for it. Imported
and ignored balances are logged to ``logs/position_init.log`` and a summary
notification is sent via ``ExceptionHandler.send_alert``.

## API endpoints

Several lightweight REST APIs expose runtime data for the dashboard.

### `/api/auto_trade_status`

- `GET` – return the current auto trading status.
  ```json
  {"enabled": false, "updated_at": "2024-05-27 10:12:11"}
  ```
- `POST` – update the status by sending `{ "enabled": true }`.

The server resets to `{"enabled": false}` whenever it starts. When disabled,
the monitoring loop continues to run so open positions and alerts remain
available via the API.

### `/api/open_positions`

- `GET` – list open positions managed by the order executor. The response is
  always a JSON array. When no positions are open it returns an empty array
  (`[]`).
  ```json
  [
    {"symbol": "KRW-BTC", "qty": 1, "status": "open"}
  ]
  ```

### `/api/events`

- `GET` – return recent event log entries from `logs/events.jsonl`.
  The optional `limit` query parameter controls how many records are returned.

### `/api/strategies`

- `GET` – return the current strategy list with on/off states and priority.
- `POST` – save an updated list. Each item should contain `short_code`, `on`
  and `order` keys. Saved settings are reloaded immediately so changes take
  effect without restarting the server.

## Dashboard data mapping

`templates/01_Home.html` fetches runtime data for the dashboard from the
new REST API endpoints. The "실시간 포지션 상세" table uses `/api/open_positions`
and the "실시간 알림/이벤트" list uses `/api/events`. `templates/02_Strategy.html`
loads and saves strategy settings via `/api/strategies`. All data is refreshed
every five seconds where applicable:

```javascript
function fetchPositions() {
  fetch('/api/open_positions')
    .then(r => r.json())
    .then(renderPositions);
}

function fetchEvents() {
  fetch('/api/events')
    .then(r => r.json())
    .then(renderEvents);
}

setInterval(fetchPositions, 5000);
setInterval(fetchEvents, 5000);
```

Each position object contains the keys `symbol`, `strategy`, `entry_price`,
`avg_price`, `current_price`, `eval_amount`, `pnl_percent`, `pyramid_count` and
`avgdown_count`. Event objects contain `timestamp` and `message`.
The `strategy` field records the name of the buy strategy used when the
position was opened.
