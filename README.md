# Chronos-Traffic

AI-driven traffic forecasting (Prophet) and road anomaly detection (CNN) for Pakistani roads.
Final Year Project, Bahria University Karachi Campus.

## Run

```bash
pip install -r requirements.txt
uvicorn backend.main:app --reload        # terminal 1: FastAPI on http://127.0.0.1:8000
streamlit run Home.py                    # terminal 2: the web app
```

`backend/traffic.db` is not in the repository (too large). Build it with `backend/database.py`
and the import scripts, then `backend/create_admin.py` (admin / pass1234) and `backend/setup_cameras.py`.

## Folder layout

| Folder / file | What it holds |
|---|---|
| `Home.py` | Landing page: pick a dataset, open the forecast dashboard |
| `pages/1_Traffic_Dashboard.py` | Public forecast page (data through FastAPI) |
| `pages/6_Sign_In.py` | Administrator sign-in |
| `pages/7_Admin_Dashboard.py` | Admin overview, forecasts, map and today's anomaly alerts |
| `pages/3_Model_Performance.py` | Prophet accuracy: MAE, RMSE, R², actual vs predicted |
| `pages/2_Historical_Analysis.py` | Recorded traffic patterns |
| `pages/4_Road_Anomaly_Detection.py` | Classify camera images / videos, anomaly history |
| `pages/5_About.py` | About page (to be updated) |
| `backend/main.py` | FastAPI: `/datasets`, `/locations`, `/directions`, `/forecast-times`, `/forecast-dashboard` (public dashboard) |
| `backend/database.py` | Database schema (creates every table) |
| `backend/auth.py` | Password check for sign-in |
| `Models/` | `traffic_anomaly_detection.keras` + `class_names.json` |
| `camera/` | Sample footage, one folder per road camera (`camera001_Karsaz_Rd`, ...) |
| `static/fonts/` | Plus Jakarta Sans font files (served by Streamlit, so the font works offline) |
| `Assets/styles/` | One CSS file per page plus `main.css` (shared), `admin.css` (all admin pages + sidebar) and `forecast_panels.css` (forecast panels used by both dashboards). The top of `main.css` lists which page loads what. |

### `utils/` (shared code, each thing defined once)

| Module | Purpose |
|---|---|
| `config.py` | Paths, backend URL, Karachi time, theme colours, constants |
| `formatting.py` | `fmt`, `num`, `clock`, `hour_label`, `level` |
| `db.py` | Read-only cached SQL (`read_sql`) and the write connection for alerts |
| `api_client.py` | Cached FastAPI calls (`fetch`) |
| `styles.py` | `load_css` |
| `ui.py` | Public page setup, divider, footer, page header with clock pill, icons, chart styling and stat cards |
| `forecast_ui.py` | Forecast picker, 6-hour panel, 7-day outlook, map (public + admin dashboards) |
| `admin_ui.py` | Admin page setup, header, route selectors, KPI cards, meters |
| `admin_nav.py` | Admin login check and sidebar |
| `anomaly_model.py` | CNN loading, image / video classification, class styles |
| `anomaly_store.py` | Saving and reading anomaly alerts |
