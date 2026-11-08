from pathlib import Path
import sqlite3

# Database location
DB_PATH = Path(__file__).resolve().parent / "traffic.db"


def get_connection():
    """Create a SQLite connection with foreign keys enabled."""
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def create_database():
    """Create the Chronos-Traffic database and its tables."""

    with get_connection() as conn:
        conn.executescript("""

        -- ==========================================
        -- 1. USERS
        -- ==========================================

        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            full_name TEXT,
            role TEXT NOT NULL
                CHECK (role IN ('admin', 'traffic_authority')),
            is_active INTEGER NOT NULL DEFAULT 1
                CHECK (is_active IN (0, 1)),
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );


        -- ==========================================
        -- 2. DATASETS
        -- ==========================================

        CREATE TABLE IF NOT EXISTS datasets (
            dataset_id INTEGER PRIMARY KEY AUTOINCREMENT,
            dataset_name TEXT NOT NULL UNIQUE,
            region TEXT,
            description TEXT,
            is_available INTEGER NOT NULL DEFAULT 0
                CHECK (is_available IN (0, 1))
        );


        -- ==========================================
        -- 3. LOCATIONS
        -- ==========================================

        CREATE TABLE IF NOT EXISTS locations (
            location_id INTEGER PRIMARY KEY AUTOINCREMENT,
            dataset_id INTEGER NOT NULL,
            source_location_id TEXT NOT NULL,
            location_name TEXT NOT NULL,
            latitude REAL,
            longitude REAL,

            UNIQUE (dataset_id, source_location_id),

            FOREIGN KEY (dataset_id)
                REFERENCES datasets(dataset_id)
        );


        -- ==========================================
        -- 4. LOCATION DIRECTIONS
        -- ==========================================

        CREATE TABLE IF NOT EXISTS location_directions (
            direction_id INTEGER PRIMARY KEY AUTOINCREMENT,
            location_id INTEGER NOT NULL,
            heading TEXT NOT NULL,

            UNIQUE (location_id, heading),

            FOREIGN KEY (location_id)
                REFERENCES locations(location_id)
        );


        -- ==========================================
        -- 5. TRAFFIC COUNTS
        -- ==========================================

        CREATE TABLE IF NOT EXISTS traffic_counts (
            count_id INTEGER PRIMARY KEY AUTOINCREMENT,
            direction_id INTEGER NOT NULL,
            datetime TEXT NOT NULL,
            vehicle_count INTEGER NOT NULL
                CHECK (vehicle_count >= 0),

            UNIQUE (direction_id, datetime),

            FOREIGN KEY (direction_id)
                REFERENCES location_directions(direction_id)
        );


        -- ==========================================
        -- 6. FORECASTS
        -- ==========================================

        CREATE TABLE IF NOT EXISTS forecasts (
            forecast_id INTEGER PRIMARY KEY AUTOINCREMENT,
            direction_id INTEGER NOT NULL,
            datetime TEXT NOT NULL,
            predicted_count REAL NOT NULL,
            yhat_lower REAL,
            yhat_upper REAL,
            traffic_percentage REAL,
            congestion TEXT,

            UNIQUE (direction_id, datetime),

            FOREIGN KEY (direction_id)
                REFERENCES location_directions(direction_id)
        );


        -- ==========================================
        -- 7. MODEL METRICS
        -- ==========================================

        CREATE TABLE IF NOT EXISTS model_metrics (
            metric_id INTEGER PRIMARY KEY AUTOINCREMENT,
            direction_id INTEGER NOT NULL,
            evaluation_type TEXT NOT NULL,
            evaluation_start TEXT,
            evaluation_end TEXT,
            actual_records INTEGER,
            matched_records INTEGER,
            mae REAL,
            rmse REAL,
            r2_score REAL,

            UNIQUE (direction_id, evaluation_type),

            FOREIGN KEY (direction_id)
                REFERENCES location_directions(direction_id)
        );


        -- ==========================================
        -- 8. FORECAST VALIDATION
        -- ==========================================

        CREATE TABLE IF NOT EXISTS forecast_validation (
            validation_id INTEGER PRIMARY KEY AUTOINCREMENT,
            direction_id INTEGER NOT NULL,
            datetime TEXT NOT NULL,
            evaluation_type TEXT NOT NULL,
            actual REAL,
            predicted REAL,
            min_predicted REAL,
            max_predicted REAL,
            error REAL,
            absolute_error REAL,
            status TEXT,

            UNIQUE (direction_id, datetime, evaluation_type),

            FOREIGN KEY (direction_id)
                REFERENCES location_directions(direction_id)
        );


        -- ==========================================
        -- 9. ANOMALY LOGS
        -- ==========================================

        CREATE TABLE IF NOT EXISTS anomaly_logs (
            anomaly_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            detected_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            anomaly_type TEXT NOT NULL,
            confidence REAL
                CHECK (confidence BETWEEN 0 AND 1),
            media_filename TEXT,

            FOREIGN KEY (user_id)
                REFERENCES users(user_id)
        );


        -- ==========================================
        -- INDEXES
        -- ==========================================

        CREATE INDEX IF NOT EXISTS idx_locations_dataset
            ON locations(dataset_id);

        CREATE INDEX IF NOT EXISTS idx_directions_location
            ON location_directions(location_id);

        CREATE INDEX IF NOT EXISTS idx_traffic_datetime
            ON traffic_counts(datetime);

        CREATE INDEX IF NOT EXISTS idx_forecasts_datetime
            ON forecasts(datetime);

        CREATE INDEX IF NOT EXISTS idx_metrics_evaluation
            ON model_metrics(evaluation_type);

        CREATE INDEX IF NOT EXISTS idx_validation_datetime
            ON forecast_validation(datetime);

        """)

    print(f"Database created successfully: {DB_PATH}")


if __name__ == "__main__":
    create_database()
