from datetime import datetime, timedelta
from pathlib import Path
import sqlite3
from contextlib import contextmanager
from fastapi import FastAPI, HTTPException, Query

DB_PATH = Path(__file__).resolve().parent / 'traffic.db'
app = FastAPI(title='Chronos-Traffic API', version='1.0')

@contextmanager
def db():
    if not DB_PATH.exists():
        raise HTTPException(503, 'SQLite database not found')
    con = sqlite3.connect(f'file:{DB_PATH.as_posix()}?mode=ro', uri=True)
    con.row_factory = sqlite3.Row
    try:
        yield con
    finally:
        con.close()

def records(cursor):
    return [dict(r) for r in cursor.fetchall()]

@app.get('/health')
def health():
    with db() as con:
        con.execute('SELECT 1')
    return {'status': 'ok'}

@app.get('/datasets')
def datasets():
    with db() as con:
        return records(con.execute('SELECT dataset_id, dataset_name, region FROM datasets WHERE is_available = 1 ORDER BY dataset_name'))

@app.get('/locations')
def locations(dataset_id: int = Query(..., ge=1)):
    with db() as con:
        return records(con.execute('SELECT location_id, location_name, latitude, longitude FROM locations WHERE dataset_id = ? ORDER BY location_name', (dataset_id,)))

@app.get('/directions')
def directions(location_id: int = Query(..., ge=1)):
    with db() as con:
        return records(con.execute('SELECT direction_id, heading FROM location_directions WHERE location_id = ? ORDER BY heading', (location_id,)))

@app.get('/forecast-range')
def forecast_range(direction_id: int = Query(..., ge=1)):
    with db() as con:
        row = con.execute('SELECT MIN(datetime) AS start, MAX(datetime) AS end FROM forecasts WHERE direction_id = ?', (direction_id,)).fetchone()
        return dict(row)

@app.get('/forecast-dashboard')
def forecast_dashboard(direction_id: int = Query(..., ge=1), reference: str = Query(...)):
    try:
        reference_dt = datetime.fromisoformat(reference)
        if reference_dt.tzinfo is not None:
            raise ValueError('Reference must be local naive datetime')
        reference = reference_dt.strftime('%Y-%m-%d %H:%M:%S')
    except ValueError:
        raise HTTPException(422, 'Use YYYY-MM-DD HH:MM:SS without timezone')
    with db() as con:
        location = con.execute('''SELECT l.location_name, l.latitude, l.longitude, ld.heading, d.dataset_name
                                  FROM location_directions ld JOIN locations l ON l.location_id=ld.location_id
                                  JOIN datasets d ON d.dataset_id=l.dataset_id WHERE ld.direction_id=?''', (direction_id,)).fetchone()
        if location is None:
            raise HTTPException(404, 'Direction not found')
        # Latest recorded observation at/before the reference timestamp, limited to same day.
        current = con.execute('''SELECT datetime, vehicle_count FROM traffic_counts
                                 WHERE direction_id=? AND datetime<=? AND datetime>=substr(?,1,10)||' 00:00:00'
                                 ORDER BY datetime DESC LIMIT 1''', (direction_id, reference, reference)).fetchone()
        # Small date-bounded result, never read the full database into the UI.
        end = (reference_dt + timedelta(days=7, hours=1)).strftime('%Y-%m-%d %H:%M:%S')
        future = records(con.execute('''SELECT datetime, predicted_count, traffic_percentage, congestion,
                                       yhat_lower, yhat_upper FROM forecasts
                                       WHERE direction_id=? AND datetime>=? AND datetime<=? ORDER BY datetime''',
                                     (direction_id, reference, end)))
        return {'location': dict(location), 'reference': reference, 'observed': dict(current) if current else None, 'forecasts': future}


# ==========================================
# MODEL PERFORMANCE ENDPOINTS
# ==========================================

@app.get('/model-metrics')
def model_metrics(direction_id: int = Query(..., ge=1)):
    """All stored evaluation results (MAE / RMSE / R2 ...) for one direction."""
    with db() as con:
        return records(con.execute('''SELECT evaluation_type, evaluation_start, evaluation_end,
                                             actual_records, matched_records, mae, rmse, r2_score
                                      FROM model_metrics WHERE direction_id = ?
                                      ORDER BY evaluation_type''', (direction_id,)))

@app.get('/model-metrics/summary')
def model_metrics_summary(dataset_id: int = Query(..., ge=1), evaluation_type: str | None = None):
    """Metrics for every direction in a dataset, used for the location comparison table."""
    sql = '''SELECT ld.direction_id, l.location_name, ld.heading, m.evaluation_type,
                    m.matched_records, m.mae, m.rmse, m.r2_score
             FROM model_metrics m
             JOIN location_directions ld ON ld.direction_id = m.direction_id
             JOIN locations l ON l.location_id = ld.location_id
             WHERE l.dataset_id = ?'''
    params = [dataset_id]
    if evaluation_type:
        sql += ' AND m.evaluation_type = ?'
        params.append(evaluation_type)
    sql += ' ORDER BY m.mae'
    with db() as con:
        return records(con.execute(sql, params))

@app.get('/validation')
def validation(direction_id: int = Query(..., ge=1), evaluation_type: str | None = None):
    """Timestamp-level actual vs predicted rows from forecast_validation."""
    sql = '''SELECT datetime, evaluation_type, actual, predicted, min_predicted, max_predicted,
                    error, absolute_error, status
             FROM forecast_validation WHERE direction_id = ?'''
    params = [direction_id]
    if evaluation_type:
        sql += ' AND evaluation_type = ?'
        params.append(evaluation_type)
    sql += ' ORDER BY datetime'
    with db() as con:
        return records(con.execute(sql, params))
