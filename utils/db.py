"""SQLite access for the Streamlit pages.

Home and the admin pages read the database directly (so admin pages still work if
FastAPI is down). The public Traffic Dashboard goes through FastAPI (utils/api_client.py).
"""
import sqlite3
from contextlib import closing

import pandas as pd
import streamlit as st

from utils.config import DB_PATH

DB_ERRORS = (sqlite3.Error, pd.errors.DatabaseError, OSError)


def connect_readonly():
    """Read-only connection: pages can never change data by accident."""
    return closing(sqlite3.connect(f"file:{DB_PATH.as_posix()}?mode=ro", uri=True))


def connect_write():
    """Read-write connection with foreign keys on (used only for anomaly alerts)."""
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    return closing(conn)


@st.cache_data(ttl=300, show_spinner=False)
def read_sql(query, params=()):
    """Cached query -> DataFrame. Reruns and page switches reuse the result for 5 minutes."""
    with connect_readonly() as conn:
        return pd.read_sql_query(query, conn, params=params)
