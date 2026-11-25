from database import get_connection

with get_connection() as conn:
    conn.execute("DROP TABLE IF EXISTS anomaly_logs")

print("anomaly_logs table removed.")