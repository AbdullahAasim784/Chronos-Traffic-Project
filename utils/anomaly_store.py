"""Saving and reading anomaly alerts (tables: anomaly_logs + cameras).

Used by the Anomaly Detection page (save after Analyze) and the Admin Dashboard
(today's alerts, Resolve / Dismiss). Rows are never deleted: "dismissed" only hides
an alert from the dashboard.
"""
import sqlite3
from contextlib import closing
from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

import pandas as pd

from backend.database import DB_PATH

KARACHI = ZoneInfo("Asia/Karachi")
TIME_FMT = "%Y-%m-%d %H:%M:%S"                  # how detected_time is stored
DUPLICATE_WINDOW = timedelta(minutes=10)       # same camera + same type within 10 min = not saved again
LOGGED_TYPES = ("accident", "flooded", "uncertain")   # normal traffic is not logged
STATUSES = ("active", "resolved", "dismissed")


def _connect():
    """Read-write connection with foreign keys on (cameras / users must exist)."""
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    return closing(conn)


def now_karachi():
    """Karachi time without timezone info, so it compares with the stored text times."""
    return datetime.now(KARACHI).replace(tzinfo=None)


def resolve_user_id(user):
    """Signed-in user dict -> users.user_id (looked up by username if the dict has no id)."""
    user = user or {}
    if user.get("user_id") is not None:
        return int(user["user_id"])
    if user.get("username"):
        with _connect() as conn:
            row = conn.execute("SELECT user_id FROM users WHERE username = ?", (user["username"],)).fetchone()
        return row[0] if row else None
    return None


def save_detection(camera_id, label, confidence_pct, user_id=None):
    """Store one detection in Karachi time. Returns (outcome, detail):

    ("saved", anomaly_id)        new alert stored
    ("duplicate", "HH:MM:SS..")  same camera + type already logged in the last 10 minutes
    ("not_logged", None)         normal traffic
    ("no_camera", None)          file is not from a registered camera folder
    """
    label = str(label).lower()
    if label not in LOGGED_TYPES:
        return "not_logged", None
    if camera_id is None:
        return "no_camera", None

    now = now_karachi()
    with _connect() as conn:
        if not conn.execute("SELECT 1 FROM cameras WHERE camera_id = ?", (camera_id,)).fetchone():
            return "no_camera", None
        recent = conn.execute(
            """SELECT detected_time FROM anomaly_logs
               WHERE camera_id = ? AND anomaly_type = ? AND detected_time >= ?
               ORDER BY detected_time DESC LIMIT 1""",
            (camera_id, label, (now - DUPLICATE_WINDOW).strftime(TIME_FMT)),
        ).fetchone()
        if recent:
            return "duplicate", recent[0]
        with conn:  # commit
            cur = conn.execute(
                """INSERT INTO anomaly_logs
                       (camera_id, user_id, detected_time, anomaly_type, confidence_score, status)
                   VALUES (?, ?, ?, ?, ?, 'active')""",
                (camera_id, user_id, now.strftime(TIME_FMT), label,
                 round(min(max(confidence_pct / 100, 0.0), 1.0), 4)),   # table stores 0-1
            )
        return "saved", cur.lastrowid


def todays_alerts():
    """Today's alerts (since 12:00 AM Karachi), newest first, without dismissed ones.
    Returns None if the anomaly table doesn't exist yet."""
    start = now_karachi().replace(hour=0, minute=0, second=0, microsecond=0)
    try:
        with _connect() as conn:
            return pd.read_sql_query(
                """SELECT a.anomaly_id, a.detected_time, a.anomaly_type, a.confidence_score, a.status,
                          COALESCE(c.camera_name, 'Camera ' || a.camera_id) AS camera_name
                   FROM anomaly_logs a LEFT JOIN cameras c ON c.camera_id = a.camera_id
                   WHERE a.detected_time >= ? AND a.status != 'dismissed'
                   ORDER BY a.detected_time DESC, a.anomaly_id DESC""",
                conn, params=(start.strftime(TIME_FMT),),
            )
    except (sqlite3.OperationalError, pd.errors.DatabaseError):   # table missing
        return None


def set_status(anomaly_id, status):
    if status not in STATUSES:
        raise ValueError(f"Unknown status: {status}")
    with _connect() as conn, conn:
        conn.execute("UPDATE anomaly_logs SET status = ? WHERE anomaly_id = ?", (status, int(anomaly_id)))


def alerts_on_day(day, camera_id=None):
    """Every alert saved on one calendar day (all statuses), newest first.
    Returns None if the anomaly table doesn't exist yet."""
    start = datetime.combine(day, time.min)
    params = [start.strftime(TIME_FMT), (start + timedelta(days=1)).strftime(TIME_FMT)]
    camera_filter = ""
    if camera_id is not None:
        camera_filter = "AND a.camera_id = ?"
        params.append(int(camera_id))
    try:
        with _connect() as conn:
            return pd.read_sql_query(
                f"""SELECT a.anomaly_id, a.detected_time, a.anomaly_type, a.confidence_score, a.status,
                           COALESCE(c.camera_name, 'Camera ' || a.camera_id) AS camera_name
                    FROM anomaly_logs a LEFT JOIN cameras c ON c.camera_id = a.camera_id
                    WHERE a.detected_time >= ? AND a.detected_time < ? {camera_filter}
                    ORDER BY a.detected_time DESC, a.anomaly_id DESC""",
                conn, params=params,
            )
    except (sqlite3.OperationalError, pd.errors.DatabaseError):
        return None


def camera_list():
    """{camera_id: camera_name} for the filters."""
    try:
        with _connect() as conn:
            return dict(conn.execute("SELECT camera_id, camera_name FROM cameras ORDER BY camera_id").fetchall())
    except sqlite3.OperationalError:
        return {}
