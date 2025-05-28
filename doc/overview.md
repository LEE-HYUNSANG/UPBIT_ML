# Project Overview

This repository implements a four stage trading system built around the Upbit exchange.

- **F1 Universe Selector** – builds a list of tradable tickers based on configurable
  filters such as volume and price. Results are stored in `config/current_universe.json`.
- **F2 Signal Engine** – evaluates OHLCV data for each symbol and produces buy/sell
  signals. The `signal_loop.py` script orchestrates data collection and executes this
  engine. Symbols from `current_universe.json` are treated as buy candidates only –
  their sell conditions are ignored until a position is opened. Sell rules are
  evaluated exclusively for coins listed in `coin_positions.json`.
  The `f2_signal` function accepts a `strategy_codes` parameter to evaluate only
  a subset of strategies when needed.
  Each OHLCV request logs a sample row so you can verify Upbit data integrity when troubleshooting.
- **F3 Order Executor** – receives signals and places orders using the Upbit API.
  It maintains open positions, handles slippage and keeps a SQLite order log. When
  linked to the Risk Manager the executor mirrors updated sizing parameters like
  `ENTRY_SIZE_INITIAL` whenever the risk configuration reloads. The executor's
  `manage_positions()` routine (internally running `hold_loop`) is invoked on every
  cycle of the signal loop and also when the application runs in monitoring mode.
  Before sending a buy order the executor verifies that the symbol is not already
  held and skips the entry if it is. Averaging down or pyramiding remains
  controlled by the risk configuration.
- **F4 Risk Manager** – enforces drawdown limits and other protections. It can pause
  or halt trading when risk thresholds are breached.
- **F5 Machine Learning Pipeline** – trains and evaluates ML models used for
  trading decisions. Scripts live in `f5_ml_pipeline/`.

A lightweight Flask application in `app.py` exposes REST API endpoints for monitoring
and control. The templates under `templates/` form a simple dashboard that consumes
those APIs.

For detailed information about the REST interface see [`api_endpoints.md`](api_endpoints.md).
Additional notes on Upbit order requirements are available in [`order_limits.md`](order_limits.md).
Startup messages about credential loading are written to `logs/F3_utils.log`.

Credential loading diagnostics are written to `logs/F3_utils.log` whenever `.env.json` is missing or malformed.

## Sell Monitoring Bar

The dashboard's "매도 모니터링" table displays a horizontal bar for each open
position. The left edge represents the stop-loss percentage while the right
edge marks the take-profit target. A small vertical indicator shows the current
price relative to the entry. Values are taken from the latest risk
configuration so changes apply automatically.

## Position Tracking

Whenever a new trade is opened the current list of holdings is written to
`config/coin_positions.json`. Each entry contains the symbol, entry price,
quantity and strategy information. This file can be inspected to see which
coins are being monitored even after restarting the application. The
`PositionManager` reloads this file at startup so any open positions continue
to be tracked across restarts.

Position data is now refreshed every second. The latest quantity, price and
PnL information are persisted back to `coin_positions.json` on each update so
external tools always see up-to-date values.

Buy orders that are submitted but not immediately filled are saved with the
status `"pending"`. While a position is pending any further buy signals for the
same symbol are ignored. Once the balance updates to a non-zero quantity the
status automatically switches to `"open"` on the next refresh.

Positions detected in the exchange account when the application boots are
registered with the origin value `"imported"` so they can be distinguished from
positions opened by automated signals.

Imported positions are monitored using all sell formulas because the placeholder strategy code is ignored.
Each position stores the strategy code used on entry. During the signal loop
only buy rules are evaluated for symbols from `current_universe.json`. Once a
position is opened its associated `sell_formula` from
`strategies_master_pruned.json` is checked on every iteration using the latest
1-minute candle. When that expression becomes `True` the coin is sold through
the order executor.

The risk configuration also defines a `HOLD_SECS` value. When a position has
been open for this many seconds the generic stop-loss, take-profit and
trailing stop rules from the "손절/익절/TS 조건" card take precedence over the
strategy-specific formula. This helps prevent very long holds.
