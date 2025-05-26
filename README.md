# UPBIT AutoTrader HS

This project contains utilities for building a trading universe and evaluating trading signals.

## Universe cache

The latest selected trading universe is saved to `config/current_universe.json`. It is written by `f1_universe.update_universe()` and loaded on startup via `load_universe_from_file()`.

External processes such as `signal_loop.py` can use this file to share the same universe.

