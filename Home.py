"""Chronos-Traffic public home page: hero, dataset picker, overview and about."""
import html
import sqlite3

import streamlit as st

from backend.database import DB_PATH
from utils.styles import load_css

st.set_page_config(
    page_title="Chronos-Traffic | Home",
    page_icon="🚦",
    layout="wide",
    initial_sidebar_state="collapsed",
)

load_css("main.css", "home.css")


@st.cache_data(ttl=60)
def get_dataset_summary():
    """Read available datasets; replace with a FastAPI call in the next phase."""
    with sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute("""
            SELECT d.dataset_id, d.dataset_name, d.region,
                   COUNT(DISTINCT l.location_id) AS locations,
                   COUNT(DISTINCT ld.direction_id) AS directions,
                   (SELECT COUNT(*) FROM forecasts f
                    JOIN location_directions fd ON f.direction_id = fd.direction_id
                    JOIN locations fl ON fd.location_id = fl.location_id
                    WHERE fl.dataset_id = d.dataset_id) AS forecasts
            FROM datasets d
            LEFT JOIN locations l ON l.dataset_id = d.dataset_id
            LEFT JOIN location_directions ld ON ld.location_id = l.location_id
            WHERE d.is_available = 1
            GROUP BY d.dataset_id
            ORDER BY d.dataset_name
        """).fetchall()
        return [dict(row) for row in rows]


def fmt(value):
    """Whole number with thousands separators."""
    return f"{int(value or 0):,}"


# ---------------------------------------------------------------
# Top bar: brand on the left, Sign In on the right
# ---------------------------------------------------------------
brand_col, _, signin_col = st.columns([3, 5, 1.3], vertical_alignment="center")

with brand_col:
    st.markdown(
        '<div class="ct-brand"><span class="ct-brand-dot"></span>Chronos-Traffic</div>',
        unsafe_allow_html=True,
    )

with signin_col:
    if st.button("Sign In", key="signin", use_container_width=True):
        st.switch_page("pages/6_Sign_In.py")


# ---------------------------------------------------------------
# Hero
# (HTML kept on single lines: indented lines inside st.markdown
#  can be treated as code blocks.)
# ---------------------------------------------------------------
st.markdown(
    '<section class="ct-hero">'
    '<div class="ct-eyebrow">INTELLIGENT TRANSPORTATION SYSTEM</div>'
    '<h1 class="ct-title">CHRONOS-TRAFFIC</h1>'
    '<div class="ct-subtitle">AI-Driven Spatio-Temporal Traffic Forecasting'
    '<br>&amp; Road Anomaly Detection</div>'
    '</section>',
    unsafe_allow_html=True,
)


# ---------------------------------------------------------------
# Load datasets
# ---------------------------------------------------------------
try:
    datasets = get_dataset_summary()
except (sqlite3.Error, OSError) as exc:
    st.error(f"Could not read the local SQLite database: {exc}")
    st.stop()

if not datasets:
    st.warning("No datasets are available yet. Import data and mark a dataset as available.")
    st.stop()

by_name = {row["dataset_name"]: row for row in datasets}

if st.session_state.get("selected_dataset_name") not in by_name:
    st.session_state["selected_dataset_name"] = next(iter(by_name))


# ---------------------------------------------------------------
# Dataset picker: compact card, selectbox and button side by side
# ---------------------------------------------------------------
with st.container(key="dataset_picker"):
    st.markdown('<div class="ct-picker-title">Choose a dataset to explore</div>', unsafe_allow_html=True)

    pick_col, go_col = st.columns([3, 2], vertical_alignment="center", gap="small")

    with pick_col:
        selected_name = st.selectbox(
            "Available traffic datasets",
            options=list(by_name),
            key="selected_dataset_name",
            label_visibility="collapsed",
        )

    selected = by_name[selected_name]
    st.session_state["selected_dataset_id"] = selected["dataset_id"]

    with go_col:
        if st.button("Explore Forecasts  →", key="explore", type="primary", use_container_width=True):
            st.switch_page("pages/1_Traffic_Dashboard.py")

    meta = []
    if selected.get("region"):
        meta.append(f'🌍 {html.escape(str(selected["region"]))}')
        
# ---------------------------------------------------------------
# Stats strip: real totals across all available datasets
# ---------------------------------------------------------------
stats = [
    ("Datasets", len(datasets), "available to explore"),
    ("Locations", sum(r["locations"] or 0 for r in datasets), "monitored road sites"),
    ("Directions", sum(r["directions"] or 0 for r in datasets), "travel directions tracked"),
    ("Forecasts", sum(r["forecasts"] or 0 for r in datasets), "stored prediction points"),
]
st.markdown(
    '<div class="ct-stats">' + "".join(
        '<div class="ct-stat">'
        f'<div class="ct-stat-value">{fmt(value)}</div>'
        f'<div class="ct-stat-label">{label}</div>'
        f'<div class="ct-stat-note">{note}</div>'
        "</div>"
        for label, value, note in stats
    ) + "</div>",
    unsafe_allow_html=True,
)


# ---------------------------------------------------------------
# System overview: one CSS grid, so all cards get equal height
# ---------------------------------------------------------------
features = [
    ("📈", "Traffic Forecasting", "Explore Prophet-based vehicle-count forecasts and predicted congestion levels."),
    ("📊", "Historical Analysis", "Discover trends and traffic patterns across locations and travel directions."),
    ("🚨", "Anomaly Detection", "Identify accidents and challenging road conditions using CNN-based image classification."),
    ("🗺️", "Location Insights", "Explore location-specific predictions and traffic conditions on a geographic view."),
]

st.markdown('<div class="ct-divider"></div>', unsafe_allow_html=True)
st.markdown(
    '<div class="ct-section-title">System Overview</div>'
    '<div class="ct-section-intro">Explore road traffic patterns, forecast upcoming conditions, '
    "and understand how intelligent analysis supports transportation decisions.</div>",
    unsafe_allow_html=True,
)
st.markdown(
    '<div class="ct-feature-grid">' + "".join(
        '<div class="ct-feature">'
        '<div class="ct-feature-head">'
        f'<span class="ct-feature-icon">{icon}</span>'
        f'<div class="ct-feature-title">{html.escape(title)}</div>'
        "</div>"
        f'<div class="ct-feature-text">{html.escape(text)}</div>'
        "</div>"
        for icon, title, text in features
    ) + "</div>",
    unsafe_allow_html=True,
)


# ---------------------------------------------------------------
# How it works: three short steps
# ---------------------------------------------------------------
steps = [
    ("Choose a dataset", "Pick a region from the selector above to load its monitored locations."),
    ("Explore forecasts", "See predicted vehicle counts and congestion levels for each location and direction."),
    ("Go deeper as admin", "Signed-in administrators get model performance, historical analysis and anomaly detection."),
]

st.markdown('<div class="ct-divider"></div>', unsafe_allow_html=True)
st.markdown('<div class="ct-section-title">How It Works</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="ct-steps">' + "".join(
        '<div class="ct-step">'
        f'<span class="ct-step-num">{i}</span>'
        "<div>"
        f'<div class="ct-step-title">{html.escape(title)}</div>'
        f'<div class="ct-step-text">{html.escape(text)}</div>'
        "</div></div>"
        for i, (title, text) in enumerate(steps, 1)
    ) + "</div>",
    unsafe_allow_html=True,
)


# ---------------------------------------------------------------
# About: text on the left, tech stack on the right
# ---------------------------------------------------------------
tech = ["Prophet", "CNN", "FastAPI", "SQLite", "Streamlit", "Plotly", "Folium"]

st.markdown('<div class="ct-divider"></div>', unsafe_allow_html=True)
st.markdown(
    '<div class="ct-about-grid">'
    "<div>"
    '<div class="ct-section-title">About Chronos-Traffic</div>'
    '<div class="ct-about">Chronos-Traffic is a final-year intelligent transportation system prototype '
    "that combines traffic forecasting with road-scene anomaly detection. Traffic forecasts are generated "
    "using Prophet, while a convolutional neural network (CNN) supports classification of normal traffic, "
    "accidents, and challenging road conditions.</div>"
    "</div>"
    '<div class="ct-tech-card">'
    '<div class="ct-tech-label">BUILT WITH</div>'
    '<div class="ct-chips">' + "".join(f'<span class="ct-chip">{t}</span>' for t in tech) + "</div>"
    "</div>"
    "</div>",
    unsafe_allow_html=True,
)


# ---------------------------------------------------------------
# Footer
# ---------------------------------------------------------------
st.markdown(
    '<div class="ct-divider"></div>'
    '<div class="ct-footnote">© 2026 Chronos-Traffic · Bahria University Karachi Campus · Final Year Project</div>',
    unsafe_allow_html=True,
)
