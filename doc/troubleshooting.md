# Troubleshooting Missing Order Executions

This page outlines the expected flow from generating buy signals to executing orders and provides checks
when orders are not executed as expected.

## Expected Flow
1. `f2_ml_buy_signal/02_ml_buy_signal.py` runs the `run()` function which saves the latest buy signals to
   `config/f2_f2_realtime_buy_list.json`.
2. `app.py` creates a scheduler thread via `start_buy_signal_scheduler()` that calls
   `buy_list_executor.execute_buy_list()` every 15 seconds. See the code around
   lines 271–294 for reference.

## Checks When Orders Are Not Executed
- Review `logs/f2/buy_list_executor.log` for lines containing **"Targets:"** and **"Executed buys"** to
  confirm the executor saw the symbols and attempted to buy them.
- Ensure the scheduler thread is running. Either run `python app.py` or manually invoke
  `start_buy_signal_scheduler()` in an interactive session.
- Verify entries in `config/f2_f2_realtime_buy_list.json` have `buy_signal` equal to `1`, `buy_count` equal to
  `0` and `pending` equal to `0`.
- Check `logs/f3/F3_order_executor.log` and `logs/f3/F3_position_manager.log` for any errors or warnings
  that might block order execution.
