import os
import sqlite3

from f3_order.replay import replay_trades


def test_replay_trades_filters_by_strategy(tmp_path):
    db = os.path.join(tmp_path, "orders.db")
    conn = sqlite3.connect(db)
    cur = conn.cursor()
    cur.execute(
        "CREATE TABLE orders (timestamp TEXT, uuid TEXT, symbol TEXT, side TEXT, qty REAL, price REAL, order_type TEXT, state TEXT, exit_type TEXT, slippage REAL, strategy_id TEXT)"
    )
    cur.executemany(
        "INSERT INTO orders VALUES (?,?,?,?,?,?,?,?,?,?,?)",
        [
            ("2021-01-01T00:00:00", "u1", "KRW-BTC", "buy", 1.0, 100.0, "limit", "done", "", 0.0, "str1"),
            ("2021-01-01T00:10:00", "u2", "KRW-BTC", "buy", 1.0, 101.0, "limit", "done", "", 0.0, "str2"),
        ],
    )
    conn.commit()
    conn.close()

    trades = list(replay_trades("2021-01-01T00:00:00", "2021-01-01T00:20:00", "str1", db))
    assert len(trades) == 1
    assert trades[0][-1] == "str1"
