"""Small UI pieces shared by public and admin pages: footer, clock pill, icons, chart styling."""
from datetime import datetime
from zoneinfo import ZoneInfo

import plotly.graph_objects as go

from utils.forecast_ui import clock

KARACHI = ZoneInfo("Asia/Karachi")

# Theme colours used in Plotly charts (CSS has the same values).
GOLD = "#f5bd57"          # brand / recorded or actual values
BLUE = "#60a5fa"          # highlights: peaks, predictions, rolling averages
RED = "#f17b83"           # misses / largest gap
SKY = "#38bdf8"           # error distribution bars

PLOT_CONFIG = {"displayModeBar": False, "scrollZoom": False}
SPIKES = dict(showspikes=True, spikemode="across", spikecolor="rgba(245,189,87,.45)",
              spikethickness=1, spikedash="dot")

FOOTER = (
    '<div class="ct-divider"></div>'
    '<div class="ct-footnote">© 2026 Chronos-Traffic · Bahria University Karachi Campus · Final Year Project</div>'
)


def now_karachi():
    return datetime.now(KARACHI)


def clock_pill(now=None):
    """Date and time pill shown under the top-right button on each page."""
    now = now or now_karachi()
    return (
        '<div class="ct-clock-wrap"><div class="ct-clock">'
        f'<span>📅 {now:%d %b %Y}</span><span class="ct-clock-sep"></span><span>🕒 {clock(now)}</span>'
        "</div></div>"
    )


# =================================================================
# Line icons (Tabler Icons, MIT licence) embedded as SVG, so they work offline.
# Colour comes from CSS (currentColor).
# =================================================================
_SVG = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
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
        font=dict(color="#bdd1e9"), showlegend=False,
        hovermode="x unified", dragmode="zoom",
        hoverlabel=dict(bgcolor="#132036", bordercolor=GOLD, font=dict(color="#eef4ff")),
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
        marker=dict(size=12, color=color, line=dict(color="#0b1220", width=2)),
    ))
    fig.add_annotation(x=x, y=y, yshift=18, showarrow=False, text=text,
                       font=dict(color=color, size=11), bgcolor="rgba(19,32,54,.85)", borderpad=3)
