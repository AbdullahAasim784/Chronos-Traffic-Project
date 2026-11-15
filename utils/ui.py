"""Shared UI pieces for every page: divider, footer, header buttons, clock pill, icons and chart styling."""
from datetime import datetime, timedelta

import plotly.graph_objects as go
import streamlit as st

from utils.config import BLUE, CHART_NOTE, CHART_TEXT, GOLD, NAVY, SURFACE, now_karachi
from utils.formatting import clock, fmt
from utils.styles import load_css

PLOT_CONFIG = {"displayModeBar": False, "scrollZoom": False}
SPIKES = dict(showspikes=True, spikemode="across", spikecolor="rgba(245,189,87,.45)",
              spikethickness=1, spikedash="dot")

FOOTER = (
    '<div class="ct-divider"></div>'
    '<div class="ct-footnote">© 2026 Chronos-Traffic · Bahria University Karachi Campus · Final Year Project</div>'
)


# =================================================================
# Page layout pieces
# =================================================================
def setup_public_page(title, icon, *page_css):
    """Page config + styles for the public pages (Home, Sign In, Traffic Dashboard).
    Admin pages use setup_admin_page() in utils/admin_ui.py instead."""
    st.set_page_config(page_title=f"Chronos-Traffic | {title}", page_icon=icon,
                       layout="wide", initial_sidebar_state="collapsed")
    load_css("main.css", *page_css, public=True)


def divider():
    """Gold-to-blue line between sections."""
    st.markdown('<div class="ct-divider"></div>', unsafe_allow_html=True)


def footer():
    st.markdown(FOOTER, unsafe_allow_html=True)


def clock_pill(now=None):
    """Date and time pill shown under the top-right button on each page."""
    now = now or now_karachi()
    return (
        '<div class="ct-clock-wrap"><div class="ct-clock">'
        f'<span>📅 {now:%d %b %Y}</span><span class="ct-clock-sep"></span><span>🕒 {clock(now)}</span>'
        "</div></div>"
    )


def page_header(title_html, button_label, button_key, target_page, sign_out=False):
    """Title block on the left; a red pill button and the date/time pill on the right, then a divider.

    Used by the Traffic Dashboard (Back to Home) and every admin page (Log Out).
    """
    left, right = st.columns([3, 2], vertical_alignment="top")
    with left:
        st.markdown(title_html, unsafe_allow_html=True)
    with right:
        if st.button(button_label, key=button_key):
            if sign_out:
                st.session_state.pop("authenticated", None)
                st.session_state.pop("user", None)
            st.switch_page(target_page)
        st.markdown(clock_pill(), unsafe_allow_html=True)
    divider()


# =================================================================
# Line icons (Tabler Icons, MIT licence) embedded as SVG, so they work offline.
# Colour comes from CSS (currentColor).
# =================================================================
_SVG = ('<svg class="ct-icon" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
        'stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">{}</svg>')
ICONS = {
    "steering-wheel": _SVG.format('<path d="M12 12m-9 0a9 9 0 1 0 18 0a9 9 0 1 0 -18 0"/>'
                                  '<path d="M12 12m-2 0a2 2 0 1 0 4 0a2 2 0 1 0 -4 0"/>'
                                  '<path d="M12 14l0 7"/><path d="M10 12l-6.75 -2"/><path d="M14 12l6.75 -2"/>'),
    "clock": _SVG.format('<path d="M3 12a9 9 0 1 0 18 0a9 9 0 0 0 -18 0"/><path d="M12 7v5l3 3"/>'),
    "route": _SVG.format('<path d="M3 19a2 2 0 1 0 4 0a2 2 0 0 0 -4 0"/><path d="M19 7a2 2 0 1 0 0 -4a2 2 0 0 0 0 4z"/>'
                         '<path d="M11 19h5.5a3.5 3.5 0 0 0 0 -7h-8a3.5 3.5 0 0 1 0 -7h4.5"/>'),
    "gauge": _SVG.format('<path d="M12 12m-9 0a9 9 0 1 0 18 0a9 9 0 1 0 -18 0"/>'
                         '<path d="M12 12m-1 0a1 1 0 1 0 2 0a1 1 0 1 0 -2 0"/>'
                         '<path d="M13.41 10.59l2.59 -2.59"/><path d="M7 12a5 5 0 0 1 5 -5"/>'),
    "ruler": _SVG.format('<path d="M19.875 12c.621 0 1.125 .512 1.125 1.143v5.714c0 .631 -.504 1.143 -1.125 1.143h-15.875'
                         'a1 1 0 0 1 -1 -1v-5.857c0 -.631 .504 -1.143 1.125 -1.143h15.75z"/><path d="M9 12v2"/>'
                         '<path d="M6 12v3"/><path d="M12 12v3"/><path d="M18 12v3"/><path d="M15 12v2"/>'
                         '<path d="M3 3v4"/><path d="M3 5h18"/><path d="M21 3v4"/>'),
    "function": _SVG.format('<path d="M3 19a2 2 0 0 0 2 2c2 0 2 -4 3 -9s1 -9 3 -9a2 2 0 0 1 2 2"/><path d="M5 12h6"/>'
                            '<path d="M15 12l6 6"/><path d="M15 18l6 -6"/>'),
    "target": _SVG.format('<path d="M12 12m-1 0a1 1 0 1 0 2 0a1 1 0 1 0 -2 0"/>'
                          '<path d="M12 12m-5 0a5 5 0 1 0 10 0a5 5 0 1 0 -10 0"/>'
                          '<path d="M12 12m-9 0a9 9 0 1 0 18 0a9 9 0 1 0 -18 0"/>'),
    "shield": _SVG.format('<path d="M11.46 20.846a12 12 0 0 1 -7.96 -14.846a12 12 0 0 0 8.5 -3a12 12 0 0 0 8.5 3'
                          'a12 12 0 0 1 -.09 7.06"/><path d="M15 19l2 2l4 -4"/>'),
    "trending-up": _SVG.format('<path d="M3 17l6 -6l4 4l8 -8"/><path d="M14 7l7 0l0 7"/>'),
    "car": _SVG.format('<path d="M7 17m-2 0a2 2 0 1 0 4 0a2 2 0 1 0 -4 0"/>'
                       '<path d="M17 17m-2 0a2 2 0 1 0 4 0a2 2 0 1 0 -4 0"/>'
                       '<path d="M5 17h-2v-6l2 -5h9l4 5h1a2 2 0 0 1 2 2v4h-2m-4 0h-6m-6 -6h15m-6 0v-5"/>'),
    "calendar-week": _SVG.format('<path d="M4 7a2 2 0 0 1 2 -2h12a2 2 0 0 1 2 2v12a2 2 0 0 1 -2 2h-12a2 2 0 0 1 -2 -2v-12z"/>'
                                 '<path d="M16 3v4"/><path d="M8 3v4"/><path d="M4 11h16"/>'
                                 '<path d="M8 14v4"/><path d="M12 14v4"/><path d="M16 14v4"/>'),
}


# =================================================================
# Plotly helpers (same dark look on every chart)
# =================================================================
def chart_layout(fig, height, y_title, x_axis):
    """Dark, transparent chart with a faint gold plot area, gold hover border and no mode bar."""
    fig.update_layout(
        height=height, margin=dict(l=10, r=10, t=30, b=10),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(245,189,87,0.03)",
        font=dict(color=CHART_TEXT), showlegend=False,
        hovermode="x unified", dragmode="zoom",
        hoverlabel=dict(bgcolor=SURFACE, bordercolor=GOLD, font=dict(color="#eef4ff")),
        xaxis=dict(showgrid=False, title=None, **x_axis),
        yaxis=dict(gridcolor="rgba(148,163,184,.12)", rangemode="tozero", title=y_title, fixedrange=True),
    )
    return fig


def gold_area(**kwargs):
    """Gold line with a fill that fades downward (flat light fill on Plotly older than 5.20)."""
    try:
        return go.Scatter(**kwargs, fill="tozeroy", fillgradient=dict(
            type="vertical", colorscale=[[0, "rgba(245,189,87,0)"], [1, "rgba(245,189,87,0.22)"]]))
    except ValueError:
        return go.Scatter(**kwargs, fill="tozeroy", fillcolor="rgba(245,189,87,0.08)")


def highlight_marker(fig, x, y, text, color=BLUE):
    """Round marker with a small label above it (peak, busiest day, largest gap...)."""
    fig.add_trace(go.Scatter(
        x=[x], y=[y], mode="markers", hoverinfo="skip", showlegend=False,
        marker=dict(size=12, color=color, line=dict(color=NAVY, width=2)),
    ))
    fig.add_annotation(x=x, y=y, yshift=18, showarrow=False, text=text,
                       font=dict(color=color, size=11), bgcolor="rgba(19,32,54,.85)", borderpad=3)


def day_axis(day):
    """X axis covering one whole day (00:00-24:00) with a tick every 2 hours."""
    start = datetime.combine(day, datetime.min.time())
    return dict(range=[start, start + timedelta(days=1)], tickformat="%H:%M",
                dtick=2 * 3600 * 1000, hoverformat="%I:%M %p", **SPIKES)


def average_line(fig, value):
    """Dotted grey line at the average, labelled 'Avg 123'."""
    fig.add_hline(
        y=value, line=dict(color="rgba(148,163,184,.55)", dash="dot", width=1),
        annotation_text=f"Avg {fmt(value)}", annotation_position="top left",
        annotation_font=dict(color=CHART_NOTE, size=10),
    )


# =================================================================
# Stat cards under a chart (styles: .ct-chart-stats in admin.css)
# =================================================================
def stat(label, value, note, cls=""):
    """One card: small label, big value (cls = peak / quiet / gold for colour), note underneath."""
    return f'<div><span>{label}</span><strong class="{cls}">{value}</strong><small>{note}</small></div>'


def chart_stats(*cards):
    """Row of stat cards built with stat()."""
    st.markdown(f'<div class="ct-chart-stats">{"".join(cards)}</div>', unsafe_allow_html=True)
