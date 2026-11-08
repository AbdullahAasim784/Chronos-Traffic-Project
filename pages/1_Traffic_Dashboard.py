"""Public traffic forecast page: route selector, 6-hour outlook, 7-day outlook and map.

The panels themselves live in utils/forecast_ui.py (shared with the Admin Dashboard).
"""
from datetime import datetime
from html import escape

import requests
import streamlit as st
from streamlit_folium import st_folium

from utils.api_client import api_get  # type: ignore
from utils.forecast_ui import (
    build_intervals, build_map, clock, fmt, interval_panel, level,
    reference_time, six_hour_trend, week_outlook,
)
from utils.styles import load_css

st.set_page_config(page_title="Traffic Forecast | Chronos-Traffic", page_icon="🚦", layout="wide")
load_css("main.css", "forecast_components.css", "forecast.css")

API_ERRORS = (requests.RequestException, ValueError)


@st.cache_data(ttl=300, show_spinner=False)
def fetch(path, **params):
    """Cached FastAPI call. Reruns reuse the response instead of asking the API again."""
    return api_get(path, params) if params else api_get(path)


# =================================================================
# Header
# =================================================================
header_left, header_right = st.columns([5, 1.5], vertical_alignment="center")
with header_left:
    st.markdown(
        '<div class="ct-title">Traffic Forecast</div>'
        '<div class="ct-subtitle">Road-level vehicle forecasts and a seven-day outlook</div>',
        unsafe_allow_html=True,
    )
with header_right:
    if st.button("← Back to Home", key="forecast_back_home"):
        st.switch_page("Home.py")


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

    route_col, selectors_col = st.columns([1.85, 1], gap="large", vertical_alignment="center")
    with selectors_col:
        st.markdown(
            '<div class="ct-dataset ct-dataset-right">Dataset: '
            f'<strong>{escape(dataset_by_id[dataset_id]["dataset_name"])}</strong></div>',
            unsafe_allow_html=True,
        )
        # Options are IDs, and each key includes its parent ID. Changing the location
        # therefore creates a fresh direction box instead of keeping a stale selection.
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
        direction_id = st.selectbox(
            "Select Direction:", list(direction_by_id),
            format_func=lambda i: direction_by_id[i]["heading"],
            key=f"forecast_direction_{location_id}",
        )

    location = location_by_id[location_id]
    direction = direction_by_id[direction_id]
    range_info = fetch("/forecast-range", direction_id=direction_id)
except API_ERRORS as exc:
    st.error(f"Could not retrieve location data: {exc}")
    st.stop()

if not range_info.get("start") or not range_info.get("end"):
    st.info("No forecasts for this road and direction.")
    st.stop()

reference, now_clock = reference_time(datetime.fromisoformat(range_info["start"]))

try:
    data = fetch(
        "/forecast-dashboard",
        direction_id=direction_id,
        reference=reference.strftime("%Y-%m-%d %H:%M:%S"),
    )
except API_ERRORS as exc:
    st.error(f"Could not retrieve forecasts: {exc}")
    st.stop()

forecast_by_dt = {datetime.fromisoformat(x["datetime"]): x for x in data["forecasts"]}

with route_col:
    st.markdown(
        '<div class="ct-route-label">SELECTED ROUTE</div>'
        f'<div class="ct-route-name">{escape(location["location_name"])}</div>'
        f'<div class="ct-route-heading">{escape(direction["heading"])}</div>'
        f'<div class="ct-forecast-date">Forecast date: <strong>{reference:%d %b %Y}</strong></div>'
        f'<div class="ct-clock-pill">🕒 Karachi/server time: {now_clock:%I:%M %p}</div>',
        unsafe_allow_html=True,
    )
st.markdown('<div class="ct-divider"></div>', unsafe_allow_html=True)


# =================================================================
# 6-hour panel and 7-day outlook (shared components)
# =================================================================
intervals, valid_intervals, peak, quiet = build_intervals(forecast_by_dt, reference)
interval_panel(intervals, peak, quiet, f"forecast_slide_{direction_id}_{reference:%Y%m%d%H%M}")

st.markdown('<div class="ct-divider"></div>', unsafe_allow_html=True)
week_outlook(forecast_by_dt, reference)


# =================================================================
# Map and road insights (70/30). Values come from stored forecasts, not live traffic.
# =================================================================
lat, lon = data["location"].get("latitude"), data["location"].get("longitude")
next_record = forecast_by_dt.get(reference) or {}
next_congestion = next_record.get("congestion") or "Unavailable"
next_count = fmt(next_record.get("predicted_count"))
trend_text, trend_class, trend_symbol, trend_note = six_hour_trend(valid_intervals)

st.markdown('<div class="ct-divider"></div>', unsafe_allow_html=True)
with st.container(key="traffic_map_panel"):
    st.markdown(
        '<div class="ct-map-heading"><div class="ct-section">Traffic Map &amp; Insights</div>'
        '<span class="ct-map-heading-note">Selected road overview</span></div>',
        unsafe_allow_html=True,
    )
    map_col, info_col = st.columns([7, 3], gap="medium", vertical_alignment="top")

    with map_col:
        if lat is None or lon is None:
            st.info("Map coordinates are unavailable for this location.")
        else:
            st_folium(
                build_map(lat, lon, location["location_name"], direction["heading"], reference, next_record),
                height=420, use_container_width=True, returned_objects=[],
                key=f"traffic_map_{direction_id}_{reference:%Y%m%d%H%M}",
            )

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
    st.markdown(
        '<div class="ct-map-note">Map marker color represents the next stored forecast, not live traffic.</div>',
        unsafe_allow_html=True,
    )

st.markdown(
    '<div class="ct-divider"></div>'
    '<div class="ct-footnote">© 2026 Chronos-Traffic · Bahria University Karachi Campus · Final Year Project</div>',
    unsafe_allow_html=True,
)
