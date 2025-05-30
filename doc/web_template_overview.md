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
