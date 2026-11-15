"""Project-wide settings: paths, backend URL, time zone and theme colours.

Every page and helper imports from here, so a path, colour or constant
is defined once for the whole app.
"""
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from backend import database

# ---------- Paths ----------
DB_PATH = database.DB_PATH      # backend/traffic.db, the one database file shared with FastAPI
ROOT = Path(__file__).resolve().parent.parent
STYLES_DIR = ROOT / "Assets" / "styles"
ICONS_DIR = ROOT / "Assets" / "icons"
MODELS_DIR = ROOT / "Models"
# Camera/camera001_Karsaz_Rd, camera002_..., works whether the folder is named "Camera" or "camera"
CAMERA_DIR = next((ROOT / n for n in ("Camera", "camera") if (ROOT / n).is_dir()), ROOT / "Camera")

# ---------- Backend ----------
API_BASE_URL = "http://127.0.0.1:8000"
API_TIMEOUT = 15            # seconds

# ---------- Time ----------
KARACHI = ZoneInfo("Asia/Karachi")
TIME_FMT = "%Y-%m-%d %H:%M:%S"      # how datetimes are stored in SQLite
INTERVALS_PER_DAY = 96              # 24 h of 15-minute records


def now_karachi():
    """Current Karachi time (timezone-aware), for display."""
    return datetime.now(KARACHI)


def karachi_naive():
    """Current Karachi time without timezone info, to compare with the stored text times."""
    return now_karachi().replace(tzinfo=None)


# ---------- Theme colours (Assets/styles/main.css uses the same values) ----------
GOLD = "#f5bd57"     # brand, recorded / actual values
BLUE = "#60a5fa"     # predicted values, second line in comparisons
RED = "#f17b83"      # peak, busiest, high congestion, accident
GREEN = "#55dca4"    # quiet, low congestion, normal traffic
AMBER = "#e5b54c"    # medium congestion
SKY = "#38bdf8"      # flooded road
GREY = "#94a3b8"     # unavailable / uncertain
NAVY = "#0b1220"     # page background
SURFACE = "#132036"  # cards, hover labels
CHART_TEXT = "#bdd1e9"
CHART_NOTE = "#9fb0c6"

# Congestion level -> colour (map marker, legends)
LEVEL_COLORS = {"low": GREEN, "medium": AMBER, "high": RED, "na": GREY}
