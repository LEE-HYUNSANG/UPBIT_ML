# Project Overview

This repository implements a four stage trading system built around the Upbit exchange.

- **F1 Universe Selector** – builds a list of tradable tickers based on configurable
  filters such as volume and price. Results are stored in `config/current_universe.json`.
- **F2 Signal Engine** – evaluates OHLCV data for each symbol and produces buy/sell
  signals. The `signal_loop.py` script orchestrates data collection and executes this
  engine.
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
