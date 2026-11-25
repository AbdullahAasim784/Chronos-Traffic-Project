"""Building blocks shared by every admin page: page setup, header,
Dataset -> Location -> Direction selectors, KPI cards, meters and panel headings.

Admin pages read SQLite directly (utils/db.py), so they work even when FastAPI is down.
"""
import html

import streamlit as st

from utils.admin_nav import admin_sidebar, require_admin
from utils.db import DB_ERRORS, read_sql
from utils.styles import load_css
from utils.ui import divider, footer, page_header


# =================================================================
# Page setup
# =================================================================
def setup_admin_page(page_title, icon, *page_css):
    """Page config + shared CSS + admin check + sidebar. Call first on every admin page."""
    st.set_page_config(
        page_title=f"Chronos-Traffic | {page_title}", page_icon=icon,
        layout="wide", initial_sidebar_state="expanded",
    )
    load_css("main.css", "admin.css", *page_css)
    # Remember which page ran last, so a page can tell "just arrived" from "rerun on the same page".
    st.session_state["ct_previous_page"] = st.session_state.get("ct_current_page")
    st.session_state["ct_current_page"] = page_title
    require_admin()
    admin_sidebar()


def footer_and_stop():
    """Footer, then stop the page (used after an error or empty-data message)."""
    footer()
    st.stop()


# =================================================================
# Header: eyebrow + gold title + subtitle on the left; Log Out and clock on the right
# =================================================================
def admin_header(title, subtitle=None):
    user = st.session_state.get("user") or {}
    name = html.escape(str(user.get("username") or user.get("name") or "Administrator"))
    welcome = f"{html.escape(subtitle)} · " if subtitle else ""
    page_header(
        '<div class="ct-admin-eyebrow">ADMINISTRATOR CONSOLE</div>'
        f'<div class="ct-admin-heading">{html.escape(title)}</div>'
        f'<div class="ct-admin-welcome">{welcome}Signed in as <strong>{name}</strong></div>',
        "↪ Log Out", "admin_top_logout", "Home.py", sign_out=True,
    )


# =================================================================
# Overview + Dataset -> Location -> Direction selectors
# =================================================================
def route_selectors(prefix, eyebrow):
    """Draw the overview rows and the three selectors. Returns (dataset, location, direction) dicts.

    Options are IDs; each key includes its parent ID, so a new location gets a fresh direction box.
    `prefix` keeps each page's selections separate (e.g. "admin", "mp", "ha").
    """
    try:
        datasets = read_sql(
            "SELECT dataset_id, dataset_name, region FROM datasets WHERE is_available = 1 ORDER BY dataset_name"
        )
    except DB_ERRORS as exc:
        st.error(f"Unable to read traffic database: {exc}")
        footer_and_stop()
    if datasets.empty:
        st.info("No available datasets found. Import a dataset first.")
        footer_and_stop()

    dataset_by_id = {int(r["dataset_id"]): r for r in datasets.to_dict("records")}
    ids = list(dataset_by_id)
    default_idx = next((i for i, d in enumerate(ids) if "karachi" in str(dataset_by_id[d]["dataset_name"]).lower()), 0)

    overview_col, filters_col = st.columns([1.35, 2], gap="large", vertical_alignment="center")
    with filters_col:
        sel_dataset, sel_location, sel_direction = st.columns(3)

    with sel_dataset:
        dataset_id = st.selectbox(
            "Dataset", ids, index=default_idx,
            format_func=lambda i: dataset_by_id[i]["dataset_name"], key=f"{prefix}_dataset",
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
                format_func=lambda i: location_by_id[i]["location_name"], key=f"{prefix}_location_{dataset_id}",
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
                format_func=lambda i: str(direction_by_id[i]["heading"]), key=f"{prefix}_direction_{location_id}",
            )
    except DB_ERRORS as exc:
        st.error(f"Could not load location/direction selectors: {exc}")
        footer_and_stop()

    dataset, location, direction = dataset_by_id[dataset_id], location_by_id[location_id], direction_by_id[direction_id]
    rows = [
        ("DATASET", dataset["dataset_name"], "dataset"),
        ("LOCATION", location["location_name"], "location"),
        ("DIRECTION", direction["heading"], "direction"),
    ]
    with overview_col:
        st.markdown(
            f'<div class="ct-admin-eyebrow">{html.escape(eyebrow)}</div><div class="ct-ov">' + "".join(
                f'<div class="ct-ov-row"><span class="ct-ov-dot {kind}"></span>'
                f'<span class="ct-ov-key">{key}</span>'
                f'<span class="ct-ov-val">{html.escape(str(value))}</span></div>'
                for key, value, kind in rows
            ) + "</div>",
            unsafe_allow_html=True,
        )
    divider()
    return dataset, location, direction


# =================================================================
# KPI cards (one CSS grid, so all four are the same size)
# =================================================================
def kpi_card(icon, label, body, desc):
    return (
        '<div class="ct-admin-kpi">'
        f'<div class="ct-kpi-head"><span class="ct-kpi-icon">{icon}</span>'
        f'<span class="ct-admin-kpi-label">{label}</span></div>'
        f"{body}"
        f'<div class="ct-admin-kpi-desc">{html.escape(desc)}</div>'
        "</div>"
    )


def kpi_grid(*cards):
    st.markdown('<div class="ct-kpi-grid">' + "".join(cards) + "</div>", unsafe_allow_html=True)


def meter(percent, blue=False):
    """Thin progress bar (0-100)."""
    width = max(0.0, min(100.0, float(percent or 0)))
    return f'<div class="ct-meter{" blue" if blue else ""}"><span style="width:{width:.1f}%"></span></div>'


def panel_heading(title, note=""):
    return (f'<div class="ct-head"><div class="ct-section">{title}</div>'
            f'<span class="ct-head-note">{note}</span></div>')
