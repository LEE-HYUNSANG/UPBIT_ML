# Web Template Overview

This project provides a simple web dashboard served at `http://localhost:3000/`.
It contains two main pages:

- **Dashboard** – shows account balance, sell monitoring, buy monitoring and
  recent alerts. Data is fetched every 5 seconds from the API endpoints.
- **알림 설정** – allows configuration of buy amount limits and Telegram
  notification options.

The "매수 설정" card on this page loads values from `/api/buy_settings` and
updates `config/f6_buy_settings.json`. It exposes the buy amount
(`ENTRY_SIZE_INITIAL`), the maximum number of coins to hold (`MAX_SYMBOLS`),
two limit order wait times (`LIMIT_WAIT_SEC_1` and `LIMIT_WAIT_SEC_2`) and the
corresponding price modes (`1st_Bid_Price` and `2nd_Bid_Price`). Default values
are `7000`, `7`, `30`, `20`, `"BID1"` and `"BID1+"` respectively.

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
