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
`config/f4_f3_latest_config.json` which controls risk parameters and order sizes.
Other modules also read from files in that directory. Changes to these files take
effect on the next loop iteration and are logged under `logs`.
