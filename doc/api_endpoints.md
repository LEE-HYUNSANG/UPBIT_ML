# REST API Endpoints

The Flask server in `app.py` exposes a minimal REST interface used by the
web dashboard. All responses are JSON encoded.

## `/api/auto_trade_status`
- **GET** – return whether automatic trading is enabled.
- **POST** – update the status. Example payload: `{ "enabled": true }`.

## `/api/open_positions`
- **GET** – list currently open positions. When no positions are open an empty
  array is returned.

## `/api/events`
- **GET** – return recent log entries from `logs/events.jsonl`. The optional
  `limit` query parameter controls how many items are returned.

## `/api/strategies`
- **GET** – fetch the strategy configuration.
- **POST** – update the list. Each item should contain the keys `short_code`,
  `on` and `order`.
