"""One-time setup for the cameras table.

1. Removes the latitude / longitude columns from `cameras` (keeps any existing rows).
2. Adds the four Karachi road cameras, using the IDs from the Camera folder names,
   so camera001_KarsazRd is camera_id 1, and so on. That way the Anomaly page and
   the database always agree on which camera is which.

Run from the project folder:   python backend/setup_cameras.py
Safe to run more than once.
"""
import re
import sqlite3
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent
DB_PATH = BACKEND_DIR / "traffic.db"
CAMERA_DIR = BACKEND_DIR.parent / "Camera"

# Display names. Keys are the camera numbers in the folder names (camera001_... -> 1).
CAMERA_NAMES = {
    1: "Karsaz Rd",
    2: "Shah re Faisal Rd",
    3: "Rashid Minhas Rd",
    4: "Hassan Square",
}


def folder_cameras():
    """Read camera numbers from the Camera folder: {1: 'camera001_KarsazRd', ...}."""
    found = {}
    if CAMERA_DIR.is_dir():
        for folder in CAMERA_DIR.iterdir():
            match = re.match(r"camera0*(\d+)_", folder.name, re.IGNORECASE)
            if folder.is_dir() and match:
                found[int(match.group(1))] = folder.name
    return found


def drop_location_columns(conn):
    """Rebuild `cameras` without latitude/longitude (the standard SQLite way; works on every version)."""
    columns = [row[1] for row in conn.execute("PRAGMA table_info(cameras)")]
    if not columns:
        conn.execute("""
            CREATE TABLE cameras (
                camera_id INTEGER PRIMARY KEY AUTOINCREMENT,
                camera_name TEXT NOT NULL UNIQUE
            )""")
        print("Created cameras table.")
        return
    if "latitude" not in columns and "longitude" not in columns:
        print("cameras table already has no latitude/longitude.")
        return

    conn.execute("""
        CREATE TABLE cameras_new (
            camera_id INTEGER PRIMARY KEY AUTOINCREMENT,
            camera_name TEXT NOT NULL UNIQUE
        )""")
    conn.execute("INSERT INTO cameras_new (camera_id, camera_name) SELECT camera_id, camera_name FROM cameras")
    conn.execute("DROP TABLE cameras")
    conn.execute("ALTER TABLE cameras_new RENAME TO cameras")
    print("Removed latitude and longitude from cameras.")


def add_cameras(conn):
    folders = folder_cameras()
    for cam_id, name in CAMERA_NAMES.items():
        # If the name is already used by another ID, free it first (keeps camera_name UNIQUE happy).
        conn.execute("DELETE FROM cameras WHERE camera_name = ? AND camera_id != ?", (name, cam_id))
        conn.execute(
            """INSERT INTO cameras (camera_id, camera_name) VALUES (?, ?)
               ON CONFLICT(camera_id) DO UPDATE SET camera_name = excluded.camera_name""",
            (cam_id, name),
        )
        folder = folders.get(cam_id, "no matching folder found")
        print(f"  camera_id {cam_id}: {name:<20} <- {folder}")

    extra = sorted(set(folders) - set(CAMERA_NAMES))
    if extra:
        print("  Note: these folders have no name in CAMERA_NAMES:", [folders[i] for i in extra])


def main():
    if not DB_PATH.exists():
        raise SystemExit(f"Database not found: {DB_PATH}")

    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = OFF")   # needed while the table is rebuilt
    try:
        with conn:                                # one transaction: all or nothing
            drop_location_columns(conn)
            add_cameras(conn)
        problems = conn.execute("PRAGMA foreign_key_check").fetchall()
        if problems:
            print("Warning: foreign key problems:", problems)
    finally:
        conn.execute("PRAGMA foreign_keys = ON")
        conn.close()

    print("\nCameras table now:")
    with sqlite3.connect(DB_PATH) as conn:
        for row in conn.execute("SELECT camera_id, camera_name FROM cameras ORDER BY camera_id"):
            print("  ", row)


if __name__ == "__main__":
    main()
