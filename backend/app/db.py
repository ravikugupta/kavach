"""
Lightweight SQLite access layer for the Kavach prototype.
"""

import sqlite3
import os
from contextlib import contextmanager

DB_PATH = os.path.join(os.path.dirname(__file__), "data", "kavach.db")


@contextmanager
def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def query(sql, params=()):
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(sql, params)
        rows = cur.fetchall()
        return [dict(row) for row in rows]


def query_one(sql, params=()):
    rows = query(sql, params)
    return rows[0] if rows else None
