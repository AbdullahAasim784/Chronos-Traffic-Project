from pathlib import Path
import sqlite3
import pandas as pd

from backend.database import get_connection, create_database

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "Data"
CHUNK_SIZE = 10_000
EVALUATION_TYPE = "future_holdout"

FILES = {
    "historical": "Victoria_telemetry_data.csv",
    "october": "Victoria_Oct_26_data.csv",
    "forecast": "Victoria_Forecast.csv",
    "metrics": "Victoria_Model_Performance.csv",
    "validation": "Victoria_Model_Validation.csv",
}


def clean(value):
    """Convert Pandas missing values to SQLite NULL."""
    if pd.isna(value):
        return None
    if hasattr(value, "item"):
        return value.item()
    return value


def timestamp(value):
    """Normalize timestamps to YYYY-MM-DD HH:MM:SS."""
    if pd.isna(value):
        return None
    return pd.Timestamp(value).strftime("%Y-%m-%d %H:%M:%S")


def read_chunks(filename):
    path = DATA / filename
    return pd.read_csv(
        path,
        chunksize=CHUNK_SIZE,
        dtype={"loc_id": str},
        low_memory=False,
    )


def register_dataset(conn):
    conn.execute("""
        INSERT OR IGNORE INTO datasets
        (dataset_name, region, description, is_available)
        VALUES (?, ?, ?, ?)
    """, (
        "Victoria",
        "Victoria, Australia",
        "Historical telemetry and Prophet traffic forecasts",
        0
    ))

    return conn.execute("""
        SELECT dataset_id FROM datasets
        WHERE dataset_name = 'Victoria'
    """).fetchone()[0]


def register_locations(conn, dataset_id):
    """Collect location and heading information from all CSVs."""
    print("\nRegistering locations and headings...")

    for filename in FILES.values():
        for chunk in read_chunks(filename):
            chunk = chunk.dropna(
                subset=["loc_id", "loc_name", "heading"]
            )

            if "latitude" in chunk.columns:
                location_cols = [
                    "loc_id", "loc_name", "latitude", "longitude"
                ]
            else:
                location_cols = ["loc_id", "loc_name"]

            locations = chunk[location_cols].drop_duplicates(
                subset=["loc_id"]
            )

            for row in locations.itertuples(index=False):
                values = row._asdict()

                conn.execute("""
                    INSERT OR IGNORE INTO locations
                    (dataset_id, source_location_id,
                     location_name, latitude, longitude)
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    dataset_id,
                    str(values["loc_id"]),
                    values["loc_name"],
                    clean(values.get("latitude")),
                    clean(values.get("longitude"))
                ))

                # Fill coordinates if this location was first
                # encountered in a CSV without coordinates.
                if "latitude" in values:
                    conn.execute("""
                        UPDATE locations
                        SET latitude = COALESCE(latitude, ?),
                            longitude = COALESCE(longitude, ?)
                        WHERE dataset_id = ?
                          AND source_location_id = ?
                    """, (
                        clean(values["latitude"]),
                        clean(values["longitude"]),
                        dataset_id,
                        str(values["loc_id"])
                    ))

            # Refresh location lookup for this dataset.
            location_map = {
                source_id: location_id
                for source_id, location_id in conn.execute("""
                    SELECT source_location_id, location_id
                    FROM locations WHERE dataset_id = ?
                """, (dataset_id,))
            }

            pairs = chunk[
                ["loc_id", "heading"]
            ].drop_duplicates()

            conn.executemany("""
                INSERT OR IGNORE INTO location_directions
                (location_id, heading)
                VALUES (?, ?)
            """, [
                (
                    location_map[str(row.loc_id)],
                    str(row.heading)
                )
                for row in pairs.itertuples(index=False)
            ])

        conn.commit()
        print("  Processed:", filename)


def direction_lookup(conn, dataset_id):
    return {
        (str(source_id), heading): direction_id
        for source_id, heading, direction_id in conn.execute("""
            SELECT l.source_location_id,
                   ld.heading,
                   ld.direction_id
            FROM location_directions ld
            JOIN locations l
              ON ld.location_id = l.location_id
            WHERE l.dataset_id = ?
        """, (dataset_id,))
    }


def import_file(conn, filename, sql, transform):
    print(f"\nImporting {filename}...")
    total = 0

    for chunk in read_chunks(filename):
        records = transform(chunk)
        conn.executemany(sql, records)
        conn.commit()

        total += len(records)
        print(f"\r  Processed {total:,} rows", end="", flush=True)

    print()
    return total


def import_counts(conn, lookup, filename):
    sql = """
        INSERT OR IGNORE INTO traffic_counts
        (direction_id, datetime, vehicle_count)
        VALUES (?, ?, ?)
    """

    def transform(chunk):
        records = []
        for row in chunk.itertuples(index=False):
            if pd.isna(row.vehicle_count):
                continue

            records.append((
                lookup[(str(row.loc_id), row.heading)],
                timestamp(row.datetime),
                int(row.vehicle_count)
            ))
        return records

    return import_file(conn, filename, sql, transform)


def import_forecasts(conn, lookup):
    sql = """
        INSERT OR IGNORE INTO forecasts
        (direction_id, datetime, predicted_count,
         yhat_lower, yhat_upper,
         traffic_percentage, congestion)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """

    def transform(chunk):
        records = []
        for row in chunk.itertuples(index=False):
            if pd.isna(row.vehicle_count):
                continue

            records.append((
                lookup[(str(row.loc_id), row.heading)],
                timestamp(row.datetime),
                float(row.vehicle_count),
                clean(row.yhat_lower),
                clean(row.yhat_upper),
                clean(row.traffic_percentage),
                clean(row.congestion)
            ))
        return records

    return import_file(
        conn, FILES["forecast"], sql, transform
    )


def import_metrics(conn, lookup):
    sql = """
        INSERT OR IGNORE INTO model_metrics
        (direction_id, evaluation_type,
         evaluation_start, evaluation_end,
         actual_records, matched_records,
         mae, rmse, r2_score)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """

    def transform(chunk):
        records = []
        for row in chunk.itertuples(index=False):
            records.append((
                lookup[(str(row.loc_id), row.heading)],
                EVALUATION_TYPE,
                "2026-10-01 00:00:00",
                "2026-10-05 23:45:00",
                clean(row.actual_records),
                clean(row.matched_records),
                clean(row.MAE),
                clean(row.RMSE),
                clean(row.R2)
            ))
        return records

    return import_file(
        conn, FILES["metrics"], sql, transform
    )


def import_validation(conn, lookup):
    sql = """
        INSERT OR IGNORE INTO forecast_validation
        (direction_id, datetime, evaluation_type,
         actual, predicted, min_predicted,
         max_predicted, error, absolute_error, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """

    def transform(chunk):
        records = []
        for row in chunk.itertuples(index=False):
            records.append((
                lookup[(str(row.loc_id), row.heading)],
                timestamp(row.datetime),
                EVALUATION_TYPE,
                clean(row.actual),
                clean(row.predicted),
                clean(row.min_predicted),
                clean(row.max_predicted),
                clean(row.error),
                clean(row.absolute_error),
                clean(row.status)
            ))
        return records

    return import_file(
        conn, FILES["validation"], sql, transform
    )


def main():
    # Check files before modifying the database.
    for filename in FILES.values():
        if not (DATA / filename).is_file():
            raise FileNotFoundError(DATA / filename)

    create_database()

    with get_connection() as conn:
        dataset_id = register_dataset(conn)
        conn.commit()

        register_locations(conn, dataset_id)
        lookup = direction_lookup(conn, dataset_id)

        print(f"\nRegistered {len(lookup)} location-heading pairs.")

        import_counts(conn, lookup, FILES["historical"])
        import_counts(conn, lookup, FILES["october"])
        import_forecasts(conn, lookup)
        import_metrics(conn, lookup)
        import_validation(conn, lookup)

        # Make dataset available only after all imports finish.
        conn.execute("""
            UPDATE datasets
            SET is_available = 1
            WHERE dataset_id = ?
        """, (dataset_id,))
        conn.commit()

    print("\nVictoria import completed successfully!")


if __name__ == "__main__":
    main()
