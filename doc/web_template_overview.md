# Web Template Overview

This project provides a simple web dashboard served at `http://localhost:3000/`.
It contains two main pages:

- **Dashboard** – shows account balance, sell monitoring, buy monitoring and
  recent alerts. Data is fetched every 5 seconds from the API endpoints.
- **알림 설정** – allows configuration of buy amount limits and Telegram
  notification options.

The "매수 설정" card on this page loads values from `/api/buy_settings` and
updates `config/f6_buy_settings.json`. It exposes five fields: the buy amount
(`ENTRY_SIZE_INITIAL`), the maximum number of coins to hold (`MAX_SYMBOLS`), the
retry count when an order fails (`MAX_RETRY`), the slippage limit (`SLIP_MAX`)
and how many times to retry a failed order (`ORDER_FAIL_RETRY`). Default values
are `10000`, `7`, `3`, `0.15` and `3` respectively.

Both pages share a dark themed layout with an auto trade toggle and server
status indicator in the header.

The dashboard shows a compact header with KRW balance and today's PnL on the
left. A sell monitoring table now occupies the right side of the first row for
quick access to open positions. Card titles use small icons for quick
recognition and share a unified font style.

## Buy Monitoring

The "매수 모니터링" table is populated from `config/f2_f2_realtime_buy_list.json`.
Whenever this file is updated the page reflects the new entries. The table spans
the entire second row of the dashboard. Expected win rate and average ROI are
displayed with one decimal place when F2 provides them, and subtle horizontal
lines improve readability. The version column shows the completion time of the
last F5 pipeline run in `MMDD_HHMM` format.
