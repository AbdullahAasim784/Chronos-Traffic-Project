"""Chronos-Traffic API (FastAPI).

Serves the public Traffic Dashboard (pages/1_Traffic_Dashboard.py). Every endpoint opens
the SQLite database read-only and returns only the rows one screen needs.
Admin pages read the database directly (utils/db.py), so they keep working if this API is down.

Run:  uvicorn backend.main:app --reload      ->  docs at http://127.0.0.1:8000/docs
"""
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timedelta

from fastapi import FastAPI, HTTPException, Query

from backend.database import DB_PATH   # same database file the Streamlit pages use

app = FastAPI(title="Chronos-Traffic API", version="1.0")
TIME_FMT = "%Y-%m-%d %H:%M:%S"          # how datetimes are stored in SQLite


# =================================================================
# Database helpers
# =================================================================
@contextmanager
def db():
    """Read-only connection for one request; rows behave like dicts (row["column"])."""
    if not DB_PATH.exists():
        raise HTTPException(503, "SQLite database not found")
    con = sqlite3.connect(f"file:{DB_PATH.as_posix()}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    try:
        yield con
    finally:
        con.close()


def records(cursor):
    """All rows of a query as a list of dicts (FastAPI turns them into JSON)."""
    return [dict(row) for row in cursor.fetchall()]


# =================================================================
# Endpoints, in the order the dashboard calls them
# =================================================================
@app.get("/health")
def health():
    """Quick check that the API is running and can open the database."""
    with db() as con:
        con.execute("SELECT 1")
    return {"status": "ok"}


@app.get("/datasets")
def datasets():
    """Datasets that can be picked on the dashboard (Victoria, Karachi)."""
    with db() as con:
        return records(con.execute(
            "SELECT dataset_id, dataset_name, region FROM datasets WHERE is_available = 1 ORDER BY dataset_name"))


@app.get("/locations")
def locations(dataset_id: int = Query(..., ge=1)):
    """Monitored roads in one dataset, with map coordinates."""
    with db() as con:
        return records(con.execute(
            """SELECT location_id, location_name, latitude, longitude
               FROM locations WHERE dataset_id = ? ORDER BY location_name""", (dataset_id,)))


@app.get("/directions")
def directions(location_id: int = Query(..., ge=1)):
    """Traffic directions (headings) of one road."""
    with db() as con:
        return records(con.execute(
            "SELECT direction_id, heading FROM location_directions WHERE location_id = ? ORDER BY heading",
            (location_id,)))


@app.get("/forecast-times")
def forecast_times(direction_id: int = Query(..., ge=1)):
    """Every forecast timestamp for one direction (feeds the date / time picker).
    Plain strings keep the reply small even for months of 15-minute forecasts."""
    with db() as con:
        return [row[0] for row in con.execute(
            "SELECT datetime FROM forecasts WHERE direction_id = ? ORDER BY datetime", (direction_id,))]


@app.get("/forecast-dashboard")
def forecast_dashboard(direction_id: int = Query(..., ge=1), reference: str = Query(...)):
    """Everything the dashboard shows for one direction from a reference time:
    the road, the last recorded count that day, and the next 7 days of forecasts."""
    try:
        reference_dt = datetime.fromisoformat(reference)
        if reference_dt.tzinfo is not None:
            raise ValueError("Reference must be a local time without timezone")
        reference = reference_dt.strftime(TIME_FMT)
    except ValueError:
        raise HTTPException(422, "Use YYYY-MM-DD HH:MM:SS without timezone")

    with db() as con:
        location = con.execute(
            """SELECT l.location_name, l.latitude, l.longitude, ld.heading, d.dataset_name
               FROM location_directions ld
               JOIN locations l ON l.location_id = ld.location_id
               JOIN datasets d ON d.dataset_id = l.dataset_id
               WHERE ld.direction_id = ?""", (direction_id,)).fetchone()
        if location is None:
            raise HTTPException(404, "Direction not found")

        # Latest recorded count at or before the reference time, on the same day only.
        observed = con.execute(
            """SELECT datetime, vehicle_count FROM traffic_counts
               WHERE direction_id = ? AND datetime <= ? AND datetime >= substr(?, 1, 10) || ' 00:00:00'
               ORDER BY datetime DESC LIMIT 1""", (direction_id, reference, reference)).fetchone()

        # Only 7 days (+1 h) of forecasts: the UI never needs the whole table.
        end = (reference_dt + timedelta(days=7, hours=1)).strftime(TIME_FMT)
        forecasts = records(con.execute(
            """SELECT datetime, predicted_count, traffic_percentage, congestion, yhat_lower, yhat_upper
               FROM forecasts WHERE direction_id = ? AND datetime >= ? AND datetime <= ?
               ORDER BY datetime""", (direction_id, reference, end)))

    return {"location": dict(location), "reference": reference,
            "observed": dict(observed) if observed else None, "forecasts": forecasts}
