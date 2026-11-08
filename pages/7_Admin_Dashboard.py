"""Chronos-Traffic admin dashboard.

Reads SQLite directly, so admin pages work even when FastAPI is down.
The 6-hour panel, week outlook and map come from utils/forecast_ui.py,
so they match the public Traffic Dashboard exactly.
"""
import html
import sqlite3
from contextlib import closing
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from streamlit_folium import st_folium

from backend.database import DB_PATH
from utils.admin_nav import admin_sidebar, require_admin
from utils.forecast_ui import (
    build_intervals, build_map, clock, fmt, interval_panel, level,
    reference_time, week_outlook,
)
from utils.styles import load_css

st.set_page_config(
    page_title="Chronos-Traffic | Admin Dashboard", page_icon="🚦",
    layout="wide", initial_sidebar_state="expanded",
)
load_css("main.css", "forecast_components.css", "admin_dashboard.css")
require_admin()
admin_sidebar()

KARACHI = ZoneInfo("Asia/Karachi")
INTERVALS_PER_DAY = 96                      # 24 h of 15-minute forecasts
ACCENT = "#2dd4bf"                          # admin accent (teal)
ACCENT_FILL = "rgba(45,212,191,0.13)"
PEAK_GOLD = "#f5bd57"
FOOTER = (
    '<div class="ct-divider"></div>'
    '<div class="ct-footnote">© 2026 Chronos-Traffic · Bahria University Karachi Campus · Final Year Project</div>'
)

# Column names the anomaly table may use. Your friend's anomaly_logs table only needs
# ONE name from each list, e.g. detected_at, anomaly_type, location_name, confidence.
ANOMALY_TIME = ("detected_at", "timestamp", "datetime", "created_at", "time")
ANOMALY_TYPE = ("anomaly_type", "type", "label", "prediction", "class_name", "category")
ANOMALY_PLACE = ("location_name", "location", "camera", "source")
ANOMALY_CONF = ("confidence", "score", "probability")


# =================================================================
# Data helpers
# =================================================================
def connect():
    return closing(sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True))


@st.cache_data(ttl=300, show_spinner=False)
def read_sql(query, params=()):
    with connect() as conn:
        return pd.read_sql_query(query, conn, params=params)


@st.cache_data(ttl=30, show_spinner=False)
def recent_anomalies(limit=8):
    """Latest anomaly rows, or None if the table doesn't exist yet. Short cache: alerts stay fresh."""
    with connect() as conn:
        exists = conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='anomaly_logs'"
        ).fetchone()
        if not exists:
            return None
        return pd.read_sql_query(f"SELECT * FROM anomaly_logs ORDER BY rowid DESC LIMIT {int(limit)}", conn)


def first_value(row, names):
    for name in names:
        value = row.get(name)
        if value is not None and pd.notna(value) and str(value).strip():
            return value
    return None


def footer_and_stop():
    st.markdown(FOOTER, unsafe_allow_html=True)
    st.stop()


# =================================================================
# Header: title left; Log Out and clock top-right
# =================================================================
user = st.session_state.get("user") or {}
user_name = user.get("username") or user.get("name") or "Administrator"
now = datetime.now(KARACHI)

head_left, head_right = st.columns([3, 2], vertical_alignment="top")
with head_left:
    st.markdown(
        '<div class="ct-admin-eyebrow">ADMINISTRATOR CONSOLE</div>'
        '<div class="ct-admin-heading">Admin Dashboard</div>'
        f'<div class="ct-admin-welcome">Signed in as <strong>{html.escape(str(user_name))}</strong></div>',
        unsafe_allow_html=True,
    )
with head_right:
    if st.button("↪ Log Out", key="admin_top_logout"):
        st.session_state.pop("authenticated", None)
        st.session_state.pop("user", None)
        st.switch_page("Home.py")
    st.markdown(
        '<div class="ct-admin-clock-wrap"><div class="ct-admin-clock">'
        f'<span>📅 {now:%d %b %Y}</span><span class="ct-clock-sep"></span><span>🕒 {clock(now)}</span>'
        "</div></div>",
        unsafe_allow_html=True,
    )
st.markdown('<div class="ct-divider"></div>', unsafe_allow_html=True)


# =================================================================
# Overview and selectors
# Options are IDs; keys include the parent ID so a new location gets a fresh direction box.
# =================================================================
try:
    datasets = read_sql(
        "SELECT dataset_id, dataset_name, region FROM datasets WHERE is_available = 1 ORDER BY dataset_name"
    )
except (sqlite3.Error, OSError) as exc:
    st.error(f"Unable to read traffic database: {exc}")
    footer_and_stop()

if datasets.empty:
    st.info("No available datasets found. Import a dataset first.")
    footer_and_stop()

dataset_by_id = {int(r["dataset_id"]): r for r in datasets.to_dict("records")}
dataset_ids = list(dataset_by_id)
default_idx = next(
    (i for i, d in enumerate(dataset_ids) if "karachi" in str(dataset_by_id[d]["dataset_name"]).lower()), 0
)

overview_col, filters_col = st.columns([1.35, 2], gap="large", vertical_alignment="center")
with filters_col:
    sel_dataset, sel_location, sel_direction = st.columns(3)

with sel_dataset:
    dataset_id = st.selectbox(
        "Dataset", dataset_ids, index=default_idx,
        format_func=lambda i: dataset_by_id[i]["dataset_name"], key="admin_dataset",
    )

try:
    locations = read_sql(
        "SELECT location_id, location_name, latitude, longitude FROM locations "
        "WHERE dataset_id = ? ORDER BY location_name", (dataset_id,),
    )
    if locations.empty:
        st.info("No locations in this dataset.")
        footer_and_stop()
    location_by_id = {int(r["location_id"]): r for r in locations.to_dict("records")}
    with sel_location:
        location_id = st.selectbox(
            "Location", list(location_by_id),
            format_func=lambda i: location_by_id[i]["location_name"], key=f"admin_location_{dataset_id}",
        )

    directions = read_sql(
        "SELECT direction_id, heading FROM location_directions WHERE location_id = ? ORDER BY heading",
        (location_id,),
    )
    if directions.empty:
        st.info("No directions available for this location.")
        footer_and_stop()
    direction_by_id = {int(r["direction_id"]): r for r in directions.to_dict("records")}
    with sel_direction:
        direction_id = st.selectbox(
            "Direction", list(direction_by_id),
            format_func=lambda i: str(direction_by_id[i]["heading"]), key=f"admin_direction_{location_id}",
        )
except sqlite3.Error as exc:
    st.error(f"Could not load location/direction selectors: {exc}")
    footer_and_stop()

dataset = dataset_by_id[dataset_id]
location = location_by_id[location_id]
direction = direction_by_id[direction_id]

with overview_col:
    rows = [
        ("DATASET", dataset["dataset_name"], "dataset"),
        ("LOCATION", location["location_name"], "location"),
        ("DIRECTION", direction["heading"], "direction"),
    ]
    st.markdown(
        '<div class="ct-admin-eyebrow">TRAFFIC OVERVIEW</div><div class="ct-ov">' + "".join(
            f'<div class="ct-ov-row"><span class="ct-ov-dot {kind}"></span>'
            f'<span class="ct-ov-key">{key}</span>'
            f'<span class="ct-ov-val">{html.escape(str(value))}</span></div>'
            for key, value, kind in rows
        ) + "</div>",
        unsafe_allow_html=True,
    )
st.markdown('<div class="ct-divider"></div>', unsafe_allow_html=True)


# =================================================================
# Forecasts for the selected direction
# =================================================================
try:
    forecast = read_sql(
        "SELECT datetime AS ts, predicted_count AS vehicles, congestion FROM forecasts "
        "WHERE direction_id = ? ORDER BY datetime", (direction_id,),
    )
except sqlite3.Error as exc:
    st.error(f"Forecast query unavailable: {exc}")
    footer_and_stop()

forecast["ts"] = pd.to_datetime(forecast["ts"], errors="coerce")
forecast["vehicles"] = pd.to_numeric(forecast["vehicles"], errors="coerce")
forecast = forecast.dropna(subset=["ts", "vehicles"])
forecast["congestion"] = forecast["congestion"].astype(object).where(forecast["congestion"].notna(), None)

if forecast.empty:
    st.info("No forecasts stored for this road and direction yet.")
    footer_and_stop()

# Same reference rule as the public page: first forecast date + next Karachi 15-minute slot.
reference, _ = reference_time(forecast["ts"].min().to_pydatetime())
forecast_by_dt = {
    ts.to_pydatetime(): {"predicted_count": float(v), "congestion": c}
    for ts, v, c in zip(forecast["ts"], forecast["vehicles"], forecast["congestion"])
}
next_24h = forecast[(forecast["ts"] >= reference) & (forecast["ts"] < reference + timedelta(hours=24))]


# =================================================================
# KPI cards (one CSS grid, so all four are the same size)
# =================================================================
# 1. Average vehicles per day, using complete days only (partial first/last days skew it low).
per_day = forecast.groupby(forecast["ts"].dt.date)["vehicles"].agg(["sum", "size"])
full_days = per_day[per_day["size"] >= INTERVALS_PER_DAY]
basis = full_days if not full_days.empty else per_day
avg_daily = basis["sum"].mean() if not basis.empty else None
avg_desc = (f"Average of {len(full_days)} full forecast day{'s' if len(full_days) != 1 else ''}"
            if not full_days.empty else "Average of partial forecast days")

# 2. Peak hour in the next 24 hours.
hourly_next = next_24h.set_index("ts")["vehicles"].resample("h").sum(min_count=1).dropna()
if hourly_next.empty:
    peak_label, peak_desc = "—", "No forecast in the next 24 h"
else:
    peak_ts = hourly_next.idxmax()
    peak_label = clock(peak_ts)
    peak_desc = f"{peak_ts:%a} · {fmt(hourly_next.max())} vehicles in that hour"

# 3. Top 3 busiest roads in the dataset. Average per 15 min, so roads whose
#    forecasts cover different dates are still compared fairly.
try:
    leaders = read_sql(
        """SELECT l.location_name, AVG(f.predicted_count) AS avg_count
           FROM forecasts f
           JOIN location_directions ld ON f.direction_id = ld.direction_id
           JOIN locations l ON ld.location_id = l.location_id
           WHERE l.dataset_id = ?
           GROUP BY l.location_id, l.location_name
           ORDER BY avg_count DESC LIMIT 3""",
        (dataset_id,),
    )
except sqlite3.Error:
    leaders = pd.DataFrame(columns=["location_name", "avg_count"])

# 4. Congestion outlook: share of the next 24 h at each level.
levels_next = next_24h["congestion"].map(level)
known = levels_next[levels_next != "na"]
shares = {k: (known == k).mean() * 100 for k in ("low", "medium", "high")} if not known.empty else {}
high_hours = (known == "high").sum() * 0.25 if not known.empty else 0


def kpi_card(icon, label, body, desc):
    return (
        '<div class="ct-admin-kpi">'
        f'<div class="ct-kpi-head"><span class="ct-kpi-icon">{icon}</span>'
        f'<span class="ct-admin-kpi-label">{label}</span></div>'
        f"{body}"
        f'<div class="ct-admin-kpi-desc">{html.escape(desc)}</div>'
        "</div>"
    )


ranking = (
    '<div class="ct-admin-ranking">' + "".join(
        f'<div class="ct-admin-rank-row"><span class="ct-rank-no">{j}</span>'
        f'<span class="ct-rank-name">{html.escape(str(r.location_name))}</span>'
        f"<strong>{fmt(r.avg_count)}</strong></div>"
        for j, r in enumerate(leaders.itertuples(index=False), 1)
    ) + "</div>"
) if not leaders.empty else '<div class="ct-admin-kpi-empty">No forecasts available</div>'

if shares:
    dominant = max(shares, key=shares.get)
    outlook = (
        f'<div class="ct-admin-kpi-value ct-cong-{dominant}">Mostly {dominant.title()}</div>'
        '<div class="ct-cong-bar">' + "".join(
            f'<span class="{k}" style="width:{shares[k]:.1f}%"></span>' for k in ("low", "medium", "high")
        ) + "</div>"
        '<div class="ct-cong-legend">' + "".join(
            f'<span><i class="{k}"></i>{k.title()} {shares[k]:.0f}%</span>' for k in ("low", "medium", "high")
        ) + "</div>"
    )
    outlook_desc = f"{high_hours:g} h of high congestion expected in the next 24 h"
else:
    outlook = '<div class="ct-admin-kpi-value">—</div>'
    outlook_desc = "No congestion labels in the next 24 h"

st.markdown(
    '<div class="ct-kpi-grid">'
    + kpi_card("🚗", "AVG VEHICLES / DAY", f'<div class="ct-admin-kpi-value">{fmt(avg_daily)}</div>', avg_desc)
    + kpi_card("⏱️", "PEAK HOUR · NEXT 24 H", f'<div class="ct-admin-kpi-value">{peak_label}</div>', peak_desc)
    + kpi_card("📍", "TOP 3 BUSIEST ROADS", ranking, "Average vehicles / 15 min across the dataset")
    + kpi_card("🚦", "CONGESTION OUTLOOK", outlook, outlook_desc)
    + "</div>",
    unsafe_allow_html=True,
)


# =================================================================
# 6-hour panel and 7-day outlook (shared with the public page)
# =================================================================
st.markdown(
    f'<div class="ct-admin-caption">Forecast reference: {reference:%d %b %Y} · {clock(reference)} '
    "· Stored predictions, not live traffic.</div>",
    unsafe_allow_html=True,
)
intervals, _, peak_slot, quiet_slot = build_intervals(forecast_by_dt, reference)
interval_panel(intervals, peak_slot, quiet_slot, f"admin_slide_{direction_id}_{reference:%Y%m%d%H%M}")

st.markdown('<div class="ct-divider"></div>', unsafe_allow_html=True)
week_outlook(forecast_by_dt, reference)


# =================================================================
# Map (shared) and anomaly alerts
# =================================================================
def alert_kind(text):
    t = str(text).lower()
    if any(w in t for w in ("accident", "crash", "collision", "fire")):
        return "high"
    if "normal" in t:
        return "low"
    return "medium"


def alerts_html(events):
    count = 0 if events is None else len(events)
    head = (
        '<div class="ct-alerts-head"><span class="ct-live-dot"></span>'
        '<span class="ct-alerts-title">ANOMALY ALERTS</span>'
        f'<span class="ct-alerts-count">{count}</span></div>'
    )
    if not count:
        note = ("Anomaly logging isn't connected yet." if events is None
                else "All monitored roads look normal.")
        body = (
            '<div class="ct-alerts-empty"><div class="ct-alerts-shield">✓</div>'
            '<div class="ct-alerts-empty-title">No anomalies detected</div>'
            f'<div class="ct-alerts-empty-text">{note} Accidents and hazardous road conditions '
            "flagged by the CNN model will appear here as instant alerts.</div></div>"
        )
    else:
        items = []
        for i, row in enumerate(events.to_dict("records"), 1):
            kind_text = str(first_value(row, ANOMALY_TYPE) or "Anomaly")
            when = first_value(row, ANOMALY_TIME)
            ts = pd.to_datetime(when, errors="coerce") if when is not None else pd.NaT
            when_text = f"{ts:%d %b} · {clock(ts)}" if pd.notna(ts) else (str(when) if when else "")
            place = first_value(row, ANOMALY_PLACE)
            conf = first_value(row, ANOMALY_CONF)
            conf_text = ""
            if conf is not None:
                try:
                    c = float(conf)
                    conf_text = f"{c * 100 if c <= 1 else c:.0f}% confidence"
                except ValueError:
                    pass
            meta = " · ".join(html.escape(str(p)) for p in (when_text, place, conf_text) if p)
            items.append(
                f'<div class="ct-alert ct-alert-{alert_kind(kind_text)}">'
                f'<span class="ct-alert-no">{i}</span>'
                f'<div><div class="ct-alert-type">{html.escape(kind_text.title())}</div>'
                f'<div class="ct-alert-meta">{meta}</div></div></div>'
            )
        body = '<div class="ct-alerts-list">' + "".join(items) + "</div>"
    return '<section class="ct-alerts">' + head + body + "</section>"


st.markdown('<div class="ct-divider"></div>', unsafe_allow_html=True)
with st.container(key="traffic_map_panel"):
    st.markdown(
        '<div class="ct-map-heading"><div class="ct-section">Location Map &amp; Anomaly Alerts</div>'
        '<span class="ct-map-heading-note">Selected road overview</span></div>',
        unsafe_allow_html=True,
    )
    map_col, alerts_col = st.columns([7, 3], gap="medium", vertical_alignment="top")
    with map_col:
        lat, lon = location.get("latitude"), location.get("longitude")
        if pd.notna(lat) and pd.notna(lon):
            st_folium(
                build_map(lat, lon, location["location_name"], direction["heading"], reference,
                          forecast_by_dt.get(reference)),
                height=420, use_container_width=True, returned_objects=[],
                key=f"admin_map_{direction_id}_{reference:%Y%m%d%H%M}",
            )
        else:
            st.info("Coordinates are unavailable for this location.")
    with alerts_col:
        try:
            events = recent_anomalies()
        except sqlite3.Error:
            events = None
        st.markdown(alerts_html(events), unsafe_allow_html=True)
    st.markdown(
        '<div class="ct-map-note">Map marker color represents the next stored forecast, not live traffic.</div>',
        unsafe_allow_html=True,
    )


# =================================================================
# 24-hour forecast chart. A fragment: changing day or resolution reruns only the chart.
# =================================================================
DAY_OPTIONS = {"Today": 0, "Tomorrow": 1, "Day After": 2}


@st.fragment
def forecast_chart(forecast, reference):
    with st.container(key="admin_chart_panel"):
        st.markdown(
            '<div class="ct-map-heading"><div class="ct-section">📈 Traffic Forecast · 24 Hours</div>'
            '<span class="ct-map-heading-note">Drag to zoom · double-click to reset</span></div>',
            unsafe_allow_html=True,
        )
        day_col, res_col = st.columns([3, 2], vertical_alignment="center")
        with day_col:
            period = st.segmented_control(
                "Forecast day", list(DAY_OPTIONS), default="Today",
                key="admin_graph_day", label_visibility="collapsed",
            )
        with res_col:
            resolution = st.segmented_control(
                "Resolution", ["Hourly", "15-min"], default="Hourly",
                key="admin_graph_res", label_visibility="collapsed",
            )

        day = reference.date() + timedelta(days=DAY_OPTIONS.get(period or "Today", 0))
        day_data = forecast[forecast["ts"].dt.date == day].set_index("ts")["vehicles"]
        if (resolution or "Hourly") == "Hourly":
            series = day_data.resample("h").sum(min_count=1).dropna()
            unit = "vehicles / hour"
        else:
            series = day_data
            unit = "vehicles / 15 min"

        if series.empty:
            st.info(f"No forecasts for {day:%A, %d %B %Y}.")
            return

        peak_ts, peak_val = series.idxmax(), series.max()
        quiet_ts, quiet_val = series.idxmin(), series.min()
        mean_val = series.mean()
        day_start = datetime.combine(day, datetime.min.time())

        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=series.index, y=series.values, mode="lines", name="Forecast",
            line=dict(color=ACCENT, width=3, shape="spline", smoothing=0.6),
            fill="tozeroy", fillcolor=ACCENT_FILL,
            hovertemplate=f"<b>%{{y:,.0f}}</b> {unit}<extra></extra>",
        ))
        fig.add_trace(go.Scatter(
            x=[peak_ts], y=[peak_val], mode="markers", hoverinfo="skip", showlegend=False,
            marker=dict(size=12, color=PEAK_GOLD, line=dict(color="#0b1220", width=2)),
        ))
        fig.add_annotation(
            x=peak_ts, y=peak_val, yshift=18, showarrow=False,
            text=f"Peak · {clock(peak_ts)}", font=dict(color=PEAK_GOLD, size=11),
        )
        fig.add_hline(
            y=mean_val, line=dict(color="rgba(148,163,184,.55)", dash="dot", width=1),
            annotation_text=f"Avg {fmt(mean_val)}", annotation_position="top left",
            annotation_font=dict(color="#9fb0c6", size=10),
        )
        if day == reference.date():
            # Shape + annotation (add_vline with text can fail on date axes).
            fig.add_shape(type="line", x0=reference, x1=reference, y0=0, y1=1, yref="paper",
                          line=dict(color="rgba(245,189,87,.6)", dash="dot", width=1))
            fig.add_annotation(x=reference, y=1, yref="paper", yshift=8, showarrow=False,
                               text="Reference", font=dict(color=PEAK_GOLD, size=10))
        fig.update_layout(
            height=360, margin=dict(l=10, r=10, t=30, b=10),
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(45,212,191,0.035)",
            font=dict(color="#bdd1e9"), showlegend=False,
            hovermode="x unified", dragmode="zoom",
            hoverlabel=dict(bgcolor="#132036", bordercolor=ACCENT, font=dict(color="#eef4ff")),
            xaxis=dict(
                range=[day_start, day_start + timedelta(days=1)], tickformat="%H:%M", dtick=2 * 3600 * 1000,
                hoverformat="%I:%M %p", showgrid=False, title=None,
                showspikes=True, spikemode="across", spikecolor="rgba(45,212,191,.45)",
                spikethickness=1, spikedash="dot",
            ),
            yaxis=dict(gridcolor="rgba(148,163,184,.12)", rangemode="tozero", title=unit, fixedrange=True),
        )
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False, "scrollZoom": False})

        st.markdown(
            '<div class="ct-chart-stats">'
            f'<div><span>Total</span><strong>{fmt(series.sum())}</strong><small>vehicles · {day:%a %d %b}</small></div>'
            f'<div><span>Peak</span><strong class="peak">{clock(peak_ts)}</strong><small>{fmt(peak_val)} {unit}</small></div>'
            f'<div><span>Quietest</span><strong class="quiet">{clock(quiet_ts)}</strong><small>{fmt(quiet_val)} {unit}</small></div>'
            f'<div><span>Average</span><strong>{fmt(mean_val)}</strong><small>{unit}</small></div>'
            "</div>",
            unsafe_allow_html=True,
        )


st.markdown('<div class="ct-divider"></div>', unsafe_allow_html=True)
forecast_chart(forecast, reference)

st.markdown(FOOTER, unsafe_allow_html=True)
