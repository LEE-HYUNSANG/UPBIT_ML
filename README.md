# UPBIT AutoTrader HS

This project contains utilities for building a trading universe and evaluating trading signals.

## Universe cache

The latest selected trading universe is saved to `config/current_universe.json`. It is written by `f1_universe.universe_selector.update_universe()` and loaded on startup via `load_universe_from_file()`.

External processes such as `signal_loop.py` can use this file to share the same universe.

## Running `signal_loop.py`

To start the F1/F2 signal loop, run:

```bash
python signal_loop.py
```

Logs are written to `logs/F1F2_loop.log`.

