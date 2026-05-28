import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "dms.db")
_SCHEMA = os.path.join(os.path.dirname(__file__), "schema.sql")


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    with open(_SCHEMA, "r") as f:
        sql = f.read()
    conn = get_connection()
    conn.executescript(sql)
    conn.commit()
    conn.close()
