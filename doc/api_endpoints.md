# REST API Endpoints

The Flask server in `app.py` exposes a simple REST interface for the web
dashboard. The server listens on the port specified by the `PORT` environment
variable (default `3000`). All responses are JSON encoded.

Logs from API calls are appended to `logs/events.jsonl` so you can trace the
history of actions from the dashboard.

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

## `/api/buy_monitoring`
- **GET** – return the contents of `config/f2_f2_realtime_buy_list.json`.
  The response includes expected win rate and average ROI if available as well
  as the last F5 completion time in `MMDD_HHMM` format.

## Using the API

The examples below use `curl` to interact with the server running locally on
port 3000.

```bash
# Check whether trading is active
curl http://localhost:3000/api/auto_trade_status

# Enable trading
curl -X POST -H "Content-Type: application/json" \
     -d '{"enabled": true}' \
     http://localhost:3000/api/auto_trade_status
```

All endpoints return a JSON object. Failures are logged in `logs/events.jsonl`.

## Configuration

API access itself requires no authentication, but the trading loop must be
configured via the JSON files under `config/`. The main file is
`config/f6_buy_settings.json` which controls order sizes and basic limits.
Changes to this file take effect on the next loop iteration and are logged
under `logs`.
