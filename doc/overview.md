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
- **F3 Order Executor** – receives signals and places orders using the Upbit API.
  It maintains open positions, handles slippage and keeps a SQLite order log. When
  linked to the Risk Manager the executor mirrors updated sizing parameters like
  `ENTRY_SIZE_INITIAL` whenever the risk configuration reloads.
- **F4 Risk Manager** – enforces drawdown limits and other protections. It can pause
  or halt trading when risk thresholds are breached.
- **F5 Machine Learning Pipeline** – trains and evaluates ML models used for
  trading decisions. Scripts live in `f5_ml_pipeline/`.

A lightweight Flask application in `app.py` exposes REST API endpoints for monitoring
and control. The templates under `templates/` form a simple dashboard that consumes
those APIs.

For detailed information about the REST interface see [`api_endpoints.md`](api_endpoints.md).
Additional notes on Upbit order requirements are available in [`order_limits.md`](order_limits.md).

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
coins are being monitored even after restarting the application.

Each position stores the strategy code used on entry. During the signal loop
only buy rules are evaluated for symbols from `current_universe.json`. Once a
position is opened its associated `sell_formula` from
`strategies_master_pruned.json` is checked on every iteration using the latest
1-minute candle. When that expression becomes `True` the coin is sold through
the order executor.
