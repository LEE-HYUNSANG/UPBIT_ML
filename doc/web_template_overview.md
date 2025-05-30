# Web Template Overview

This project provides a simple web dashboard served at `http://localhost:3000/`.
It contains two main pages:

- **Dashboard** – shows account balance, sell monitoring, buy monitoring and
  recent alerts. Data is fetched every 5 seconds from the API endpoints.
- **알림 설정** – allows configuration of buy amount limits and Telegram
  notification options.

Both pages share a dark themed layout with an auto trade toggle and server
status indicator in the header.

The dashboard now displays four cards at the top showing KRW balance, daily
profit and loss, monitored coins, and the current auto trade status for better
readability.

## Buy Monitoring

The "매수 모니터링" table is populated from `config/f2_f2_realtime_buy_list.json`.
Whenever this file is updated the page reflects the new entries. Expected win
rate and average ROI are shown when F2 provides them. The version column
displays the completion time of the last F5 pipeline run in `MMDD_HHMM` format.
