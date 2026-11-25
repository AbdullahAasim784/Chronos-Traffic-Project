"""One-time update for the anomaly_logs table.

Changes the allowed status values from ('new', 'acknowledged') to
('active', 'resolved', 'dismissed') with 'active' as the default,
and adds an index on detected_time (the dashboard filters by day).
Existing rows are kept: new -> active, acknowledged -> resolved.

Run from the project folder:   python backend/update_anomaly_status.py
Safe to run more than once.
"""
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent / "traffic.db"

NEW_TABLE = """
CREATE TABLE anomaly_logs_new (
    anomaly_id INTEGER PRIMARY KEY AUTOINCREMENT,
    camera_id INTEGER NOT NULL,
    user_id INTEGER,
    detected_time TEXT NOT NULL
        DEFAULT (datetime('now', 'localtime')),
    anomaly_type TEXT NOT NULL,
    confidence_score REAL
        CHECK (confidence_score BETWEEN 0 AND 1),
    status TEXT NOT NULL DEFAULT 'active'
        CHECK (status IN ('active', 'resolved', 'dismissed')),

    FOREIGN KEY (camera_id)
        REFERENCES cameras(camera_id),
    FOREIGN KEY (user_id)
        REFERENCES users(user_id)
)"""


def main():
    if not DB_PATH.exists():
        raise SystemExit(f"Database not found: {DB_PATH}")

    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = OFF")   # needed while the table is rebuilt
    try:
        row = conn.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='anomaly_logs'").fetchone()
        if row is None:
            raise SystemExit("anomaly_logs table not found. Run your create_database script first.")

        with conn:  # one transaction: all or nothing
            if "'dismissed'" in row[0]:
                print("anomaly_logs already uses active / resolved / dismissed.")
            else:
                conn.execute(NEW_TABLE)
                conn.execute("""
                    INSERT INTO anomaly_logs_new
                        (anomaly_id, camera_id, user_id, detected_time, anomaly_type, confidence_score, status)
                    SELECT anomaly_id, camera_id, user_id, detected_time, anomaly_type, confidence_score,
                           CASE status WHEN 'acknowledged' THEN 'resolved' ELSE 'active' END
                    FROM anomaly_logs""")
                conn.execute("DROP TABLE anomaly_logs")
                conn.execute("ALTER TABLE anomaly_logs_new RENAME TO anomaly_logs")
                print("Status values updated to: active / resolved / dismissed (default: active).")

            conn.execute("CREATE INDEX IF NOT EXISTS idx_anomaly_camera ON anomaly_logs(camera_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_anomaly_time ON anomaly_logs(detected_time)")

        problems = conn.execute("PRAGMA foreign_key_check(anomaly_logs)").fetchall()
        if problems:
            print("Warning: rows pointing to missing cameras/users:", problems)
        count = conn.execute("SELECT COUNT(*) FROM anomaly_logs").fetchone()[0]
        print(f"anomaly_logs ready ({count} existing row{'s' if count != 1 else ''} kept).")
    finally:
        conn.execute("PRAGMA foreign_keys = ON")
        conn.close()


if __name__ == "__main__":
    main()
