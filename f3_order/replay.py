import sqlite3
from datetime import datetime


def replay_trades(start_date: str, end_date: str, strategy_id: str, db_path: str = "logs/f3/orders.db"):
    """Iterate over trades stored in the orders database.

    Parameters
    ----------
    start_date : str
        ISO formatted start date.
    end_date : str
        ISO formatted end date.
    strategy_id : str
        Identifier of the strategy to filter by.
    db_path : str, optional
        Path to the SQLite database file.

    Yields
    ------
    tuple
        Rows from the ``orders`` table matching the criteria.
    """
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute(
        "SELECT * FROM orders WHERE timestamp BETWEEN ? AND ? AND strategy_id = ?",
        (start_date, end_date, strategy_id),
    )
    for row in cur.fetchall():
        yield row
    conn.close()


