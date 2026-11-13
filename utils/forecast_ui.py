"""Shared forecast UI for the public Traffic Dashboard and the Admin Dashboard.

Both pages call these functions, so the 6-hour panel, the 7-day outlook and the map
look and behave the same everywhere. Styles: Assets/styles/forecast_components.css.
"""
import base64
from datetime import datetime, timedelta
from html import escape
from pathlib import Path
from zoneinfo import ZoneInfo

import folium
import streamlit as st
from folium.plugins import Fullscreen

ROOT = Path(__file__).resolve().parent.parent
ICON_PATH = ROOT / "Assets" / "icons" / "traffic_road_icon.png"

WINDOW_SIZE = 8      # interval slots visible at once
SLIDE_STEP = 8       # slots moved per arrow click (set to 1 to move one interval at a time)
OUTLOOK_SLOTS = 25   # 6 hours of 15-minute intervals (inclusive)
LEVEL_COLORS = {"low": "#55dca4", "medium": "#e5b54c", "high": "#f17b83", "na": "#94a3b8"}

# Line icons (Tabler Icons, MIT) as inline SVG; colour comes from CSS (currentColor).
_SVG = ('<svg class="ct-icon" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" '
        'stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round" '
        'aria-hidden="true">{}</svg>')
ICON_CLOCK = _SVG.format('<path d="M3 12a9 9 0 1 0 18 0a9 9 0 0 0 -18 0"/><path d="M12 7v5l3 3"/>')
ICON_CAR = _SVG.format('<path d="M7 17m-2 0a2 2 0 1 0 4 0a2 2 0 1 0 -4 0"/>'
                       '<path d="M17 17m-2 0a2 2 0 1 0 4 0a2 2 0 1 0 -4 0"/>'
                       '<path d="M5 17h-2v-6l2 -5h9l4 5h1a2 2 0 0 1 2 2v4h-2m-4 0h-6m-6 -6h15m-6 0v-5"/>')


# =================================================================
# Small helpers
# =================================================================
def fmt(value):
    if value is None or value != value:  # None or NaN
        return "—"
    return f"{round(value):,}"


def level(congestion):
    """Map a congestion label to one CSS suffix: low / medium / high / na."""
    key = str(congestion or "").strip().lower()
    if key == "low":
        return "low"
    if key in ("medium", "moderate"):
        return "medium"
    if key == "high":
        return "high"
    return "na"


def clock(dt):
    return dt.strftime("%I:%M %p").lstrip("0")


def reference_time(first_forecast, available=None):
    """Earliest forecast date for a direction, at the next Karachi 15-minute slot.

    If `available` (a set/dict of forecast datetimes) is given, the date moves forward
    until a forecast exists at that clock time. This stops a road whose first forecast
    day starts late (e.g. 11 PM) from showing "Unavailable" everywhere.
    """
    now = datetime.now(ZoneInfo("Asia/Karachi"))
    next_slot = now.replace(second=0, microsecond=0) + timedelta(minutes=15 - now.minute % 15)
    reference = datetime.combine(first_forecast.date(), next_slot.time())
    if next_slot.date() != now.date():  # 23:45+ rolls over to the next day
        reference += timedelta(days=1)
    if available:
        for _ in range(14):  # look ahead at most two weeks
            if reference in available:
                break
            reference += timedelta(days=1)
        else:
            reference = datetime.combine(first_forecast.date(), next_slot.time())
    return reference, now


def karachi_now():
    """Karachi time without timezone info (forecast times are stored that way)."""
    return datetime.now(ZoneInfo("Asia/Karachi")).replace(tzinfo=None)


def _minutes(t):
    return t.hour * 60 + t.minute


def default_reference(times):
    """Starting forecast time for the date/time picker. Returns (reference, note).

    Uses the next Karachi 15-minute slot on the earliest day that has a forecast at that time.
    If no day has that time (e.g. Karachi data covers 8 AM-3 PM and it is now 4 PM),
    it snaps to the nearest time that does exist and explains why in `note`.
    """
    times = sorted(times)
    now = karachi_now()
    slot = (now.replace(second=0, microsecond=0) + timedelta(minutes=15 - now.minute % 15)).time()
    exact = next((t for t in times if t.time() == slot), None)
    if exact is not None:
        return exact, None
    tods = sorted({t.time() for t in times})
    best = min(tods, key=lambda tod: abs(_minutes(tod) - _minutes(slot)))
    reference = next(t for t in times if t.time() == best)
    note = (f"Forecasts for this road cover {clock(tods[0])} – {clock(tods[-1])} each day, "
            f"so {clock(best)} is shown instead of {clock(slot)}.")
    return reference, note


def forecast_picker(times, key, date_col, time_col):
    """Forecast date (calendar) + time (15-minute steps) pickers. Returns (reference, note).

    If the chosen date/time has no forecast (outside the data's hours or dates),
    the nearest available forecast time is used and `note` says so.
    """
    times = sorted(times)
    available = set(times)
    default, default_note = default_reference(times)
    dates = sorted({t.date() for t in times})
    with date_col:
        day = st.date_input("Forecast date", value=default.date(), min_value=dates[0], max_value=dates[-1],
                            format="DD/MM/YYYY", key=f"{key}_date")
    with time_col:
        tod = st.time_input("Forecast time", value=default.time(), step=timedelta(minutes=15), key=f"{key}_time")

    wanted = datetime.combine(day, tod)
    if wanted in available:
        return wanted, (default_note if wanted == default else None)

    # Nearest day that has forecasts, then the nearest 15-minute slot on that day.
    near_day = min(dates, key=lambda d: abs((d - day).days))
    day_times = [t for t in times if t.date() == near_day]
    reference = min(day_times, key=lambda t: abs(_minutes(t) - _minutes(tod)))
    note = (f"No forecast at {wanted:%d %b} · {clock(wanted)}. "
            f"Showing the nearest available time: {reference:%d %b} · {clock(reference)}.")
    return reference, note


def reference_caption(reference, note=None):
    """'Forecast reference: ...' line shown above the 6-hour panel (left side)."""
    return (
        f'<div class="ct-ref-caption">Forecast reference: <strong>{reference:%a, %d %b %Y} · {clock(reference)}</strong>'
        " · Stored predictions, not live traffic.</div>"
        + (f'<div class="ct-snap-note">{escape(note)}</div>' if note else "")
    )


@st.cache_data(show_spinner=False)
def icon_data_uri(path_str):
    """Inline the road icon so it sits in the same HTML block as the count."""
    path = Path(path_str)
    if not path.is_file():
        return None
    return "data:image/png;base64," + base64.b64encode(path.read_bytes()).decode()


# =================================================================
# 6-hour outlook
# =================================================================
def build_intervals(forecast_by_dt, reference):
    """Quarter-hour slots from the reference time, plus peak and quietest slot."""
    intervals = []
    for i in range(OUTLOOK_SLOTS):
        target = reference + timedelta(minutes=15 * i)
        record = forecast_by_dt.get(target) or {}
        value = record.get("predicted_count")
        intervals.append({
            "time": clock(target),
            "value": value,
            "count": fmt(value),
            "congestion": record.get("congestion") or "Unavailable",
        })
    # Trim unavailable slots at the end; gaps in the middle stay visible.
    while intervals and intervals[-1]["value"] is None:
        intervals.pop()
    valid = [item for item in intervals if item["value"] is not None]
    peak = max(valid, key=lambda x: x["value"]) if valid else None
    quiet = min(valid, key=lambda x: x["value"]) if valid else None
    return intervals, valid, peak, quiet


def six_hour_trend(valid):
    """Compare first and last available values. Direction of change, not live traffic."""
    if len(valid) < 2:
        return "Unavailable", "unavailable", "—", "Not enough forecasts to compare"
    first, last = float(valid[0]["value"]), float(valid[-1]["value"])
    diff = last - first
    note = f"{fmt(first)} to {fmt(last)} vehicles / 15 min"
    if first > 0 and abs(diff) / first <= 0.05:
        return "Relatively stable", "stable", "→", note
    if diff > 0:
        return "Increasing", "increasing", "↗", note
    if diff < 0:
        return "Decreasing", "decreasing", "↘", note
    return "Stable", "stable", "→", note


def _shift_slots(state_key, delta, max_start):
    """Arrow callback: move the window and remember the direction for the slide animation."""
    current = st.session_state.get(state_key, 0)
    st.session_state[state_key] = max(0, min(max_start, current + delta))
    st.session_state["slide_dir"] = "next" if delta > 0 else "prev"
    st.session_state["slide_tick"] = st.session_state.get("slide_tick", 0) + 1


def _unit(value):
    """Small "veh" after a count, like °C after a temperature."""
    return '<span class="ct-veh">veh</span>' if value is not None and value == value else ""


def _slot_html(item, is_current, offset, total, slide_dir, tick):
    classes = "ct-native-slot"
    if is_current:
        classes += " is-current"
    if slide_dir:
        # Alternating -0/-1 class names restart the CSS animation on every click.
        classes += f" ct-slide-{slide_dir}-{tick}"
    # Right-to-left stagger only when going back; left-to-right otherwise (also on load).
    delay = total - 1 - offset if slide_dir == "prev" else offset
    return (
        f'<div class="{classes}" style="--delay:{delay}">'
        f'<div class="ct-panel-slot-time">{escape(item["time"])}</div>'
        f'<div class="ct-panel-slot-count">{escape(item["count"])}{_unit(item["value"])}</div>'
        f'<div class="ct-panel-slot-level {level(item["congestion"])}">{escape(item["congestion"])}</div>'
        "</div>"
    )


@st.fragment
def interval_panel(intervals, peak, quiet, state_key, reference=None):
    """The 6-hour panel. A fragment: arrow clicks rerun only this panel.
    `reference` adds the Forecast date / Forecast time block next to the count."""
    first = intervals[0] if intervals else None

    with st.container(key="forecast_interval_panel"):
        st.markdown(
            '<div class="ct-panel-header"><span class="ct-panel-kicker">' + ICON_CLOCK + 'UPCOMING TRAFFIC FORECAST</span>'
            '<span class="ct-panel-hint">6-hour outlook</span></div>',
            unsafe_allow_html=True,
        )

        # Third column is a small spacer so the insights sit between the middle and the right edge.
        # main_col | insights_col | spacer. Smaller last number = insights further right.
        main_col, insights_col, _ = st.columns([2, 1.1, 0.06], gap="large", vertical_alignment="center")

        with main_col:
            icon = icon_data_uri(str(ICON_PATH))
            icon_html = f'<img class="ct-panel-icon" src="{icon}" alt="">' if icon else ""
            congestion = first["congestion"] if first else "Unavailable"
            when = (
                '<div class="ct-panel-when">'
                f'<div><span>FORECAST DATE</span><strong>{reference:%a, %d %b %Y}</strong></div>'
                f'<div><span>FORECAST TIME</span><strong>{clock(reference)}</strong></div></div>'
            ) if reference is not None else ""
            st.markdown(
                '<div class="ct-panel-main">' + icon_html + "<div>"
                '<div class="ct-panel-count-row">'
                f'<span class="ct-panel-count">{escape(first["count"] if first else "—")}</span>'
                '<span class="ct-panel-unit">vehicles / 15 min</span></div>'
                '<div class="ct-panel-status">'
                f'<span class="{level(congestion)}">Congestion: {escape(congestion)}</span>'
                "</div></div>" + when + "</div>",
                unsafe_allow_html=True,
            )

        with insights_col:
            for label, item, symbol, kind in (
                ("PEAK TRAFFIC EXPECTED", peak, "↗", "peak"),
                ("LOWEST PREDICTED TRAFFIC", quiet, "✓", "quiet"),
            ):
                detail = f'{item["count"]} vehicles / 15 min · {item["congestion"]}' if item else "No forecast available"
                st.markdown(
                    f'<div class="ct-panel-insight"><span class="ct-insight-icon {kind}">{symbol}</span><div>'
                    f'<div class="ct-insight-label">{label}</div>'
                    f'<div class="ct-insight-time">{escape(item["time"] if item else "—")}</div>'
                    f'<div class="ct-insight-detail">{escape(detail)}</div>'
                    "</div></div>",
                    unsafe_allow_html=True,
                )

        st.markdown('<div class="ct-panel-rule"></div>', unsafe_allow_html=True)

        max_start = max(0, len(intervals) - WINDOW_SIZE)
        start = min(st.session_state.setdefault(state_key, 0), max_start)
        slide_dir = st.session_state.pop("slide_dir", None)   # animate only right after a click
        tick = st.session_state.get("slide_tick", 0) % 2

        prev_col, slots_col, next_col = st.columns([0.55, 10, 0.55], gap="small", vertical_alignment="center")
        with prev_col:
            # The visible arrow is drawn in CSS; the text label stays for screen readers.
            st.button(
                "Previous", key="ct_prev_interval", disabled=start == 0,
                help="Previous forecast intervals",
                on_click=_shift_slots, args=(state_key, -SLIDE_STEP, max_start),
            )
        with slots_col:
            visible = intervals[start:start + WINDOW_SIZE]
            if visible:
                for offset, (col, item) in enumerate(zip(st.columns(len(visible), gap="small"), visible)):
                    with col:
                        st.markdown(
                            _slot_html(item, start + offset == 0, offset, len(visible), slide_dir, tick),
                            unsafe_allow_html=True,
                        )
        with next_col:
            st.button(
                "Next", key="ct_next_interval", disabled=start >= max_start,
                help="Next forecast intervals",
                on_click=_shift_slots, args=(state_key, SLIDE_STEP, max_start),
            )


# =================================================================
# 7-day outlook: same clock time on each of the next seven days.
# A missing record stays "Unavailable"; dates are never shifted to fill gaps.
# =================================================================
def week_outlook(forecast_by_dt, reference):
    days = []
    for day_offset in range(7):
        target = reference + timedelta(days=day_offset)
        record = forecast_by_dt.get(target) or {}
        congestion = record.get("congestion") or "Unavailable"
        days.append(
            f'<div class="ct-week-day" title="{escape(target.strftime("%A, %d %B %Y"))}">'
            f'<div class="ct-week-weekday">{target:%a}</div>'
            f'<div class="ct-week-date">{target:%d %b}</div>'
            f'<div class="ct-week-count">{escape(fmt(record.get("predicted_count")))}{_unit(record.get("predicted_count"))}</div>'
            f'<div class="ct-week-status ct-week-{level(congestion)}">{escape(congestion)}</div>'
            "</div>"
        )
    st.markdown(
        '<div class="ct-week-heading"><div class="ct-section">Upcoming Week Forecast</div>'
        '<span class="ct-week-heading-note">7-day outlook</span></div>'
        '<div class="ct-week-description">Predicted vehicle counts per 15-minute interval, '
        "compared at the same time across seven days.</div>"
        '<section class="ct-week-panel" aria-label="Upcoming week traffic forecast">'
        '<div class="ct-week-grid">' + "".join(days) + "</div>"
        '<div class="ct-week-footer"><span class="ct-week-ico">' + ICON_CAR + '</span> Vehicle counts / 15 min '
        '<span class="ct-week-footer-dot">·</span> <span class="ct-week-ico">' + ICON_CLOCK + '</span> '
        f"Compared at {escape(clock(reference))}</div></section>",
        unsafe_allow_html=True,
    )


# =================================================================
# Map: marker coloured by the next stored forecast (not live traffic).
# =================================================================
def build_map(lat, lon, place, heading, reference, record):
    lat, lon = float(lat), float(lon)
    record = record or {}
    congestion = record.get("congestion") or "Unavailable"
    count = fmt(record.get("predicted_count"))
    color = LEVEL_COLORS[level(congestion)]

    traffic_map = folium.Map(
        location=[lat, lon], zoom_start=13, tiles="OpenStreetMap",
        control_scale=True, scrollWheelZoom=False, prefer_canvas=True,
    )
    Fullscreen(position="topright", title="Expand map", title_cancel="Exit full screen").add_to(traffic_map)
    popup_html = (
        '<div style="min-width:200px;color:#111827">'
        f"<strong>{escape(str(place))}</strong><br>"
        f"Direction: {escape(str(heading))}<br>"
        f'Forecast: {escape(reference.strftime("%d %b %Y, ") + clock(reference))}<br>'
        f"Vehicles / 15 min: {escape(count)}<br>"
        f"Congestion: <strong>{escape(congestion)}</strong></div>"
    )
    folium.CircleMarker(
        location=[lat, lon], radius=20, color=color, weight=3,
        fill=True, fill_color=color, fill_opacity=0.24,
        tooltip=f"{escape(str(place))} · {escape(str(heading))}",
        popup=folium.Popup(popup_html, max_width=320),
    ).add_to(traffic_map)
    folium.Marker(
        location=[lat, lon], icon=folium.Icon(color="blue", icon="info-sign"),
        popup=folium.Popup(popup_html, max_width=320),
    ).add_to(traffic_map)
    return traffic_map
