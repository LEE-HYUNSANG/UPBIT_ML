import sqlite3
from datetime import datetime


def replay_trades(start_date: str, end_date: str, strategy_id: str, db_path: str = "logs/orders.db"):
    """Yield historical trades between start and end date for a given strategy."""
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute(
        "SELECT * FROM orders WHERE timestamp BETWEEN ? AND ?",
        (start_date, end_date),
    )
    for row in cur.fetchall():
        yield row
    conn.close()


def run_integration_tests():
    """Run pytest and return the exit code."""
    import subprocess
    return subprocess.call(["pytest", "-q"])  # pragma: no cover
