"""Chronos-Traffic admin dashboard.

Reads SQLite directly, so admin pages work even when FastAPI is down.
The 6-hour panel, week outlook and map come from utils/forecast_ui.py,
so they match the public Traffic Dashboard exactly.
"""
import html
import sqlite3
from datetime import datetime, timedelta

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from streamlit_folium import st_folium

from utils.admin_ui import (
    admin_header, connect, divider, footer_and_stop, kpi_card, kpi_grid,
    panel_heading, read_sql, route_selectors, setup_admin_page,
)
from utils.forecast_ui import (
    build_intervals, build_map, clock, fmt, interval_panel, level,
    reference_time, week_outlook,
)
from utils.ui import BLUE, FOOTER, GOLD, ICONS, PLOT_CONFIG, SPIKES, chart_layout, gold_area, highlight_marker

setup_admin_page("Admin Dashboard", "🚦", "forecast_components.css", "admin_dashboard.css")

INTERVALS_PER_DAY = 96                      # 24 h of 15-minute forecasts

# Column names the anomaly table may use. Your friend's anomaly_logs table only needs
# ONE name from each list, e.g. detected_at, anomaly_type, location_name, confidence.
ANOMALY_TIME = ("detected_at", "timestamp", "datetime", "created_at", "time")
ANOMALY_TYPE = ("anomaly_type", "type", "label", "prediction", "class_name", "category")
ANOMALY_PLACE = ("location_name", "location", "camera", "source")
ANOMALY_CONF = ("confidence", "score", "probability")


# =================================================================
# Anomaly alerts data
# =================================================================
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


admin_header("Admin Dashboard")
dataset, location, direction = route_selectors("admin", "TRAFFIC OVERVIEW")
dataset_id, direction_id = int(dataset["dataset_id"]), int(direction["direction_id"])


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

forecast_by_dt = {
    ts.to_pydatetime(): {"predicted_count": float(v), "congestion": c}
    for ts, v, c in zip(forecast["ts"], forecast["vehicles"], forecast["congestion"])
}
# First forecast date + next Karachi 15-minute slot, moved forward to the first day
# that actually has a forecast at that time (so the panels never open on an empty day).
reference, _ = reference_time(forecast["ts"].min().to_pydatetime(), forecast_by_dt)
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

kpi_grid(
    kpi_card(ICONS["steering-wheel"], "AVG VEHICLES / DAY", f'<div class="ct-admin-kpi-value">{fmt(avg_daily)}</div>', avg_desc),
    kpi_card(ICONS["clock"], "PEAK HOUR · NEXT 24 H", f'<div class="ct-admin-kpi-value">{peak_label}</div>', peak_desc),
    kpi_card(ICONS["route"], "TOP 3 BUSIEST ROADS", ranking, "Average vehicles / 15 min across the dataset"),
    kpi_card(ICONS["gauge"], "CONGESTION OUTLOOK", outlook, outlook_desc),
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

divider()
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


divider()
with st.container(key="traffic_map_panel"):
    st.markdown(panel_heading("Location Map &amp; Anomaly Alerts", "Selected road overview"), unsafe_allow_html=True)
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
    with st.container(key="panel_forecast_chart"):
        st.markdown(panel_heading("📈 Traffic Forecast · 24 Hours", "Drag to zoom · double-click to reset"),
                    unsafe_allow_html=True)
        day_col, res_col = st.columns([3, 2], vertical_alignment="center")
        with day_col:
            period = st.segmented_control(
                "Forecast day", list(DAY_OPTIONS), default="Today",
                key="admin_graph_day", label_visibility="collapsed",
            )
        with res_col:
            resolution = st.segmented_control(
                "Resolution", ["Hourly", "15-min"], default="Hourly",
                key="res_admin_chart", label_visibility="collapsed",
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
        fig.add_trace(gold_area(
            x=series.index, y=series.values, mode="lines", name="Forecast",
            line=dict(color=GOLD, width=3, shape="spline", smoothing=0.6),
            hovertemplate=f"<b>%{{y:,.0f}}</b> {unit}<extra></extra>",
        ))
        highlight_marker(fig, peak_ts, peak_val, f"Peak · {clock(peak_ts)}")
        fig.add_hline(
            y=mean_val, line=dict(color="rgba(148,163,184,.55)", dash="dot", width=1),
            annotation_text=f"Avg {fmt(mean_val)}", annotation_position="top left",
            annotation_font=dict(color="#9fb0c6", size=10),
        )
        if day == reference.date():
            # Shape + annotation (add_vline with text can fail on date axes).
            fig.add_shape(type="line", x0=reference, x1=reference, y0=0, y1=1, yref="paper",
                          line=dict(color="rgba(96,165,250,.6)", dash="dot", width=1))
            fig.add_annotation(x=reference, y=1, yref="paper", yshift=8, showarrow=False,
                               text="Reference", font=dict(color=BLUE, size=10))
        chart_layout(fig, 360, unit, dict(
            range=[day_start, day_start + timedelta(days=1)], tickformat="%H:%M", dtick=2 * 3600 * 1000,
            hoverformat="%I:%M %p", **SPIKES,
        ))
        st.plotly_chart(fig, use_container_width=True, config=PLOT_CONFIG)

        st.markdown(
            '<div class="ct-chart-stats">'
            f'<div><span>Total</span><strong>{fmt(series.sum())}</strong><small>vehicles · {day:%a %d %b}</small></div>'
            f'<div><span>Peak</span><strong class="peak">{clock(peak_ts)}</strong><small>{fmt(peak_val)} {unit}</small></div>'
            f'<div><span>Quietest</span><strong class="quiet">{clock(quiet_ts)}</strong><small>{fmt(quiet_val)} {unit}</small></div>'
            f'<div><span>Average</span><strong>{fmt(mean_val)}</strong><small>{unit}</small></div>'
            "</div>",
            unsafe_allow_html=True,
        )


divider()
forecast_chart(forecast, reference)

st.markdown(FOOTER, unsafe_allow_html=True)
