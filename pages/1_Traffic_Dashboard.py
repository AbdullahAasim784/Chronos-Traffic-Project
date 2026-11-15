"""Public traffic forecast page: route selector, 6-hour outlook, 7-day outlook and map.

The panels themselves live in utils/forecast_ui.py (shared with the Admin Dashboard).
"""
from datetime import datetime
from html import escape

import streamlit as st

from utils.api_client import API_ERRORS, fetch
from utils.formatting import clock, fmt, level
from utils.forecast_ui import (
    build_intervals, interval_panel, map_note, map_view, picker_row, six_hour_trend, week_outlook,
)
from utils.ui import divider, footer, page_header, setup_public_page

setup_public_page("Traffic Forecast", "🚦", "forecast_panels.css", "traffic_dashboard.css")


# =================================================================
# Header: title left; Back to Home and the date / time pill right
# =================================================================
page_header(
    '<div class="ct-title">Traffic Forecast</div>'
    '<div class="ct-subtitle">Road-level vehicle forecasts and a seven-day outlook</div>',
    "← Back to Home", "forecast_back_home", "Home.py",
)


# =================================================================
# Dataset, location and direction
# =================================================================
try:
    datasets = fetch("/datasets")
except API_ERRORS as exc:
    st.error(f"Cannot connect to FastAPI. Start the backend first. Details: {exc}")
    st.stop()

if not datasets:
    st.warning("No available datasets.")
    st.stop()

dataset_by_id = {d["dataset_id"]: d for d in datasets}
dataset_id = st.session_state.get("selected_dataset_id")
if dataset_id not in dataset_by_id:
    dataset_id = next(iter(dataset_by_id))
    st.session_state["selected_dataset_id"] = dataset_id

try:
    locations = fetch("/locations", dataset_id=dataset_id)
    if not locations:
        st.info("No locations for this dataset.")
        st.stop()
    location_by_id = {loc["location_id"]: loc for loc in locations}

    # Route summary left, selectors right. The selectors sit side by side in a wider
    # column, so they reach into the middle of the page instead of leaving a gap.
    route_col, selectors_col = st.columns([1, 1.25], gap="large", vertical_alignment="center")
    with selectors_col:
        st.markdown(
            '<div class="ct-dataset ct-dataset-right">Dataset: '
            f'<strong>{escape(dataset_by_id[dataset_id]["dataset_name"])}</strong></div>',
            unsafe_allow_html=True,
        )
        location_col, direction_col = st.columns(2, gap="medium")
        # Options are IDs, and each key includes its parent ID. Changing the location
        # therefore creates a fresh direction box instead of keeping a stale selection.
        with location_col:
            location_id = st.selectbox(
                "Select Location:", list(location_by_id),
                format_func=lambda i: location_by_id[i]["location_name"],
                key=f"forecast_location_{dataset_id}",
            )
        directions = fetch("/directions", location_id=location_id)
        if not directions:
            st.info("No directions for this location.")
            st.stop()
        direction_by_id = {d["direction_id"]: d for d in directions}
        with direction_col:
            direction_id = st.selectbox(
                "Select Direction:", list(direction_by_id),
                format_func=lambda i: direction_by_id[i]["heading"],
                key=f"forecast_direction_{location_id}",
            )

    location = location_by_id[location_id]
    direction = direction_by_id[direction_id]
    # Every forecast time for this direction (feeds the date / time picker).
    times = [datetime.fromisoformat(t) for t in fetch("/forecast-times", direction_id=direction_id)]
except API_ERRORS as exc:
    st.error(f"Could not retrieve location data: {exc}")
    st.stop()

if not times:
    st.info("No forecasts for this road and direction.")
    st.stop()

with route_col:
    st.markdown(
        '<div class="ct-route"><div class="ct-route-label">SELECTED ROUTE</div><div class="ct-ov">'
        '<div class="ct-ov-row"><span class="ct-ov-dot location"></span><span class="ct-ov-key">LOCATION</span>'
        f'<span class="ct-ov-val location">{escape(location["location_name"])}</span></div>'
        '<div class="ct-ov-row"><span class="ct-ov-dot direction"></span><span class="ct-ov-key">DIRECTION</span>'
        f'<span class="ct-ov-val direction">{escape(direction["heading"])}</span></div></div></div>',
        unsafe_allow_html=True,
    )
divider()


# =================================================================
# Row above the 6-hour panel: reference text left, Forecast date + time pickers right.
# Starts at the next Karachi 15-minute slot, or the nearest time this road has forecasts for.
# =================================================================
reference = picker_row(times, f"forecast_{direction_id}")
try:
    data = fetch("/forecast-dashboard", direction_id=direction_id, reference=reference.strftime("%Y-%m-%d %H:%M:%S"))
except API_ERRORS as exc:
    st.error(f"Could not retrieve forecasts: {exc}")
    st.stop()
forecast_by_dt = {datetime.fromisoformat(x["datetime"]): x for x in data["forecasts"]}


# =================================================================
# 6-hour panel and 7-day outlook (shared components)
# =================================================================
intervals, valid_intervals, peak, quiet = build_intervals(forecast_by_dt, reference)
interval_panel(intervals, peak, quiet, f"forecast_slide_{direction_id}_{reference:%Y%m%d%H%M}", reference)

divider()
week_outlook(forecast_by_dt, reference)


# =================================================================
# Map and road insights (70/30). Values come from stored forecasts, not live traffic.
# =================================================================
next_record = forecast_by_dt.get(reference) or {}
next_congestion = next_record.get("congestion") or "Unavailable"
next_count = fmt(next_record.get("predicted_count"))
trend_text, trend_class, trend_symbol, trend_note = six_hour_trend(valid_intervals)

divider()
with st.container(key="traffic_map_panel"):
    st.markdown(
        '<div class="ct-head"><div class="ct-section">Traffic Map &amp; Insights</div>'
        '<span class="ct-head-note">Selected road overview</span></div>',
        unsafe_allow_html=True,
    )
    map_col, info_col = st.columns([7, 3], gap="medium", vertical_alignment="top")

    with map_col:
        map_view(data["location"], direction["heading"], reference, next_record,
                 key=f"traffic_map_{direction_id}_{reference:%Y%m%d%H%M}")

    with info_col:
        st.markdown(
            '<section class="ct-map-details" aria-label="Road and traffic insights">'
            '<div class="ct-map-kicker">ROAD INFORMATION</div>'
            '<div class="ct-map-label">Selected road</div>'
            f'<div class="ct-map-value ct-map-road">{escape(location["location_name"])}</div>'
            f'<div class="ct-map-value ct-map-direction">{escape(direction["heading"])}</div>'
            '<div class="ct-map-separator"></div>'
            f'<div class="ct-map-label">Next forecast · {escape(clock(reference))}</div>'
            f'<div class="ct-map-count">{escape(next_count)}<span> vehicles / 15 min</span></div>'
            f'<div class="ct-map-status ct-map-{level(next_congestion)}">● {escape(next_congestion)} congestion</div>'
            '<div class="ct-map-separator"></div>'
            '<div class="ct-map-label">6-HOUR TRAFFIC TREND</div>'
            f'<div class="ct-map-trend ct-map-trend-{trend_class}">'
            f'<span aria-hidden="true">{trend_symbol}</span> {escape(trend_text)}</div>'
            f'<div class="ct-map-trend-note">{escape(trend_note)}</div>'
            '<div class="ct-map-separator"></div>'
            '<div class="ct-map-label">TRAFFIC INTENSITY</div>'
            '<div class="ct-map-legend">'
            '<span><i class="ct-map-dot ct-map-dot-low"></i> Low</span>'
            '<span><i class="ct-map-dot ct-map-dot-medium"></i> Medium</span>'
            '<span><i class="ct-map-dot ct-map-dot-high"></i> High</span>'
            "</div></section>",
            unsafe_allow_html=True,
        )
    map_note()

footer()
