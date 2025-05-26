"""
F4 RiskLogger - 리스크/상태/이벤트 로그 및 알림
"""
import logging
import os
import sqlite3

class RiskLogger:
    def __init__(self, log_path, db_path="logs/risk_events.db"):
        self.logger = logging.getLogger("F4_risk_manager")
        os.makedirs(os.path.dirname(log_path), exist_ok=True)
        fh = logging.FileHandler(log_path, encoding="utf-8")
        formatter = logging.Formatter('%(asctime)s [F4] %(levelname)s %(message)s')
        fh.setFormatter(formatter)
        self.logger.addHandler(fh)
        self.logger.setLevel(logging.INFO)

        self.db_path = db_path
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        cur.execute(
            "CREATE TABLE IF NOT EXISTS risk_events (timestamp TEXT, state TEXT, message TEXT)"
        )
        conn.commit()
        conn.close()

    def _log_db(self, state, msg):
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO risk_events VALUES (datetime('now'), ?, ?)",
            (state, msg),
        )
        conn.commit()
        conn.close()

    def info(self, msg):
        self.logger.info(msg)
        self._log_db("INFO", msg)

    def warn(self, msg):
        self.logger.warning(msg)
        self._log_db("WARN", msg)

    def critical(self, msg):
        self.logger.critical(msg)
        self._log_db("CRITICAL", msg)
