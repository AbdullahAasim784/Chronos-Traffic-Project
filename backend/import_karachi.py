from pathlib import Path
import pandas as pd

from backend.database import get_connection, create_database

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "Data"

# ==========================================================
# Karachi files (inside the Data folder)
# ==========================================================
FILES = {
    "counts": "Karachi_dataset_0800-1500.csv",
    "forecast": "Karachi_Forecast.csv",
    "metrics": "Karachi_Model_Performance.csv",
    "validation": "Karachi_Model_Validation.csv",
}

DATASET_NAME = "Karachi"
REGION = "Karachi, Pakistan"
DESCRIPTION = "YOLO-World video counts (Karsaz) and Prophet traffic forecasts"

EVALUATION_TYPE = "leave_one_day_out"
EVALUATION_START = "2026-09-15 08:00:00"
EVALUATION_END = "2026-09-18 15:00:00"


def clean(value):
    """Convert Pandas missing values to SQLite NULL."""
    if value is None or pd.isna(value):
        return None
    if hasattr(value, "item"):
        return value.item()
    return value


def timestamp(value):
    """Normalize timestamps to YYYY-MM-DD HH:MM:SS."""
    if pd.isna(value):
        return None
    return pd.Timestamp(value).strftime("%Y-%m-%d %H:%M:%S")


def load(name):
    """Read a Karachi CSV and make its columns match the database."""
    df = pd.read_csv(DATA / FILES[name], dtype={"loc_id": str})

    # Same loc_id everywhere, even if Excel turned 0001 into 1
    df["loc_id"] = df["loc_id"].str.strip().str.zfill(4)

    # Counts file uses "vehicle_counts"
    df = df.rename(columns={"vehicle_counts": "vehicle_count"})

    # Performance file: older version had "tested_records"
    if "tested_records" in df.columns:
        df["actual_records"] = df["tested_records"]
        df["matched_records"] = df["tested_records"]

    # Validation file: older version had no "status"
    if name == "validation" and "status" not in df.columns:
        df["status"] = "Available"

    return df


def main():
    # Check files before touching the database
    for filename in FILES.values():
        if not (DATA / filename).is_file():
            raise FileNotFoundError(DATA / filename)

    counts = load("counts")
    forecast = load("forecast")
    metrics = load("metrics")
    validation = load("validation")

    create_database()

    with get_connection() as conn:

        # ---------- Dataset ----------
        conn.execute("""
            INSERT OR IGNORE INTO datasets
            (dataset_name, region, description, is_available)
            VALUES (?, ?, ?, 0)
        """, (DATASET_NAME, REGION, DESCRIPTION))

        dataset_id = conn.execute(
            "SELECT dataset_id FROM datasets WHERE dataset_name = ?",
            (DATASET_NAME,)
        ).fetchone()[0]

        # ---------- Locations & headings ----------
        locs = counts[["loc_id", "loc_name", "latitude", "longitude", "heading"]].drop_duplicates()

        for row in locs.itertuples(index=False):
            conn.execute("""
                INSERT OR IGNORE INTO locations
                (dataset_id, source_location_id, location_name, latitude, longitude)
                VALUES (?, ?, ?, ?, ?)
            """, (dataset_id, row.loc_id, row.loc_name, clean(row.latitude), clean(row.longitude)))

            location_id = conn.execute("""
                SELECT location_id FROM locations
                WHERE dataset_id = ? AND source_location_id = ?
            """, (dataset_id, row.loc_id)).fetchone()[0]

            conn.execute("""
                INSERT OR IGNORE INTO location_directions (location_id, heading)
                VALUES (?, ?)
            """, (location_id, row.heading))

        lookup = {
            (source_id, heading): direction_id
            for source_id, heading, direction_id in conn.execute("""
                SELECT l.source_location_id, ld.heading, ld.direction_id
                FROM location_directions ld
                JOIN locations l ON ld.location_id = l.location_id
                WHERE l.dataset_id = ?
            """, (dataset_id,))
        }

        # Every file must refer to a known location-heading
        for name, df in [("forecast", forecast), ("metrics", metrics), ("validation", validation)]:
            missing = set(zip(df["loc_id"], df["heading"])) - set(lookup)
            if missing:
                raise ValueError(f"{FILES[name]} has unknown location/heading: {missing}")

        # ---------- Traffic counts ----------
        conn.executemany("""
            INSERT OR IGNORE INTO traffic_counts (direction_id, datetime, vehicle_count)
            VALUES (?, ?, ?)
        """, [
            (lookup[(r.loc_id, r.heading)], timestamp(r.datetime), int(r.vehicle_count))
            for r in counts.itertuples(index=False)
        ])

        # ---------- Forecasts ----------
        conn.executemany("""
            INSERT OR IGNORE INTO forecasts
            (direction_id, datetime, predicted_count, yhat_lower, yhat_upper,
             traffic_percentage, congestion)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, [
            (lookup[(r.loc_id, r.heading)], timestamp(r.datetime), float(r.vehicle_count),
             clean(r.yhat_lower), clean(r.yhat_upper),
             clean(r.traffic_percentage), clean(r.congestion))
            for r in forecast.itertuples(index=False)
        ])

        # ---------- Model metrics ----------
        conn.executemany("""
            INSERT OR IGNORE INTO model_metrics
            (direction_id, evaluation_type, evaluation_start, evaluation_end,
             actual_records, matched_records, mae, rmse, r2_score)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, [
            (lookup[(r["loc_id"], r["heading"])], EVALUATION_TYPE, EVALUATION_START, EVALUATION_END,
             clean(r.get("actual_records")), clean(r.get("matched_records")),
             clean(r.get("MAE")), clean(r.get("RMSE")), clean(r.get("R2")))
            for r in metrics.to_dict("records")
        ])

        # ---------- Forecast validation ----------
        conn.executemany("""
            INSERT OR IGNORE INTO forecast_validation
            (direction_id, datetime, evaluation_type, actual, predicted,
             min_predicted, max_predicted, error, absolute_error, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, [
            (lookup[(r.loc_id, r.heading)], timestamp(r.datetime), EVALUATION_TYPE,
             clean(r.actual), clean(r.predicted), clean(r.min_predicted), clean(r.max_predicted),
             clean(r.error), clean(r.absolute_error), clean(r.status))
            for r in validation.itertuples(index=False)
        ])

        # Make dataset available only after everything is stored
        conn.execute("UPDATE datasets SET is_available = 1 WHERE dataset_id = ?", (dataset_id,))
        conn.commit()

        # ---------- Summary ----------
        print("=" * 60)
        print("KARACHI IMPORT COMPLETED")
        print("=" * 60)
        print("Dataset ID          :", dataset_id)
        for table in ["traffic_counts", "forecasts", "model_metrics", "forecast_validation"]:
            n = conn.execute(f"""
                SELECT COUNT(*) FROM {table} t
                JOIN location_directions ld ON t.direction_id = ld.direction_id
                JOIN locations l ON ld.location_id = l.location_id
                WHERE l.dataset_id = ?
            """, (dataset_id,)).fetchone()[0]
            print(f"{table:<20}: {n}")


if __name__ == "__main__":
    main()
