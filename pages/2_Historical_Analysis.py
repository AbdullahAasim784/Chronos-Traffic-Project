"""Chronos-Traffic | Historical Analysis (admin page).

Recorded traffic counts for one road and direction from the traffic_counts table.
Reads SQLite directly (same as the Admin Dashboard), so it works when FastAPI is down.
"""
import sqlite3
from datetime import datetime, timedelta

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from utils.admin_ui import (
    admin_header, divider, footer_and_stop, kpi_card, kpi_grid, meter,
    panel_heading, read_sql, route_selectors, setup_admin_page,
)
from utils.forecast_ui import clock, fmt
from utils.ui import FOOTER, GOLD, ICONS, PLOT_CONFIG, RED, SPIKES, chart_layout, gold_area, highlight_marker

setup_admin_page("Historical Analysis", "🗄️", "historical_analysis.css")

INTERVALS_PER_DAY = 96                       # 24 h of 15-minute records
USABLE_SHARE = 0.9                           # a day counts for averages if >= 90% of its intervals exist
MIN_INTERVALS = int(INTERVALS_PER_DAY * USABLE_SHARE)   # 86 of 96
WEEKDAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
WEEKDAY_NAMES = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


def num(value, digits=1):
    if value is None or pd.isna(value):
        return "—"
    return f"{value:,.{digits}f}"


def hour_label(hour):
    return clock(datetime(2000, 1, 1, int(hour)))


admin_header("Historical Analysis", "Recorded traffic patterns from the telemetry dataset")
dataset, location, direction = route_selectors("ha", "HISTORICAL OVERVIEW")
direction_id = int(direction["direction_id"])
location_name, heading = location["location_name"], direction["heading"]


# =================================================================
# Recorded counts for the selected direction
# =================================================================
try:
    history = read_sql(
        "SELECT datetime, vehicle_count FROM traffic_counts WHERE direction_id = ? ORDER BY datetime",
        (direction_id,),
    ).copy()
except sqlite3.Error as exc:
    st.error(f"Traffic records unavailable: {exc}")
    footer_and_stop()

history["datetime"] = pd.to_datetime(history["datetime"], errors="coerce")
history["vehicle_count"] = pd.to_numeric(history["vehicle_count"], errors="coerce")
history = history.dropna(subset=["datetime", "vehicle_count"])

if history.empty:
    st.info("No recorded traffic is stored for this road and direction yet.")
    footer_and_stop()

history["date"] = history["datetime"].dt.date
history["weekday"] = history["datetime"].dt.dayofweek
history["slot"] = history["datetime"].dt.strftime("%H:%M")

first_ts, last_ts = history["datetime"].min(), history["datetime"].max()
span_days = (last_ts.date() - first_ts.date()).days + 1
expected = span_days * INTERVALS_PER_DAY
completeness = len(history) / expected * 100 if expected else None

# Per-day totals. Daily averages only use "usable" days (>= 90% of the 96 intervals recorded),
# so days cut short by missing data don't drag the averages down.
per_day = history.groupby("date")["vehicle_count"].agg(["sum", "size", "mean"])
usable_days = per_day[per_day["size"] >= MIN_INTERVALS]
basis = usable_days if not usable_days.empty else per_day

# Hourly totals for every hour in the record (gaps stay gaps, never filled).
hourly = history.set_index("datetime")["vehicle_count"].resample("h").sum(min_count=1).dropna().to_frame("vehicles")
hourly["hour"] = hourly.index.hour
hourly["weekday"] = hourly.index.dayofweek


# =================================================================
# Data summary: short paragraph + completeness meter
# =================================================================
missing = max(0, expected - len(history))
st.markdown(
    '<div class="ct-summary"><div>'
    '<div class="ct-admin-eyebrow">DATA SUMMARY</div>'
    f"<p>This road has <strong>{fmt(len(history))}</strong> recorded 15-minute intervals, from "
    f'<span class="ct-hl">{first_ts:%d %b %Y}</span> to <span class="ct-hl">{last_ts:%d %b %Y}</span>, '
    f"across <strong>{fmt(len(per_day))} days</strong>. "
    f"<strong>{fmt(len(usable_days))}</strong> of them have at least 90% of their intervals recorded "
    "and are used for the daily averages. "
    + (f'<span class="ct-hl bright">{fmt(missing)} intervals are missing</span> and are shown as gaps, not filled in.'
       if missing else "No intervals are missing in this period.")
    + "</p></div>"
    '<div class="ct-summary-side">'
    '<div class="ct-summary-top"><span class="ct-summary-label">DATA COMPLETENESS</span>'
    f'<span class="ct-summary-value">{num(completeness)}%</span></div>'
    f"{meter(completeness)}"
    f'<div class="ct-summary-legend"><span>Recorded <b>{fmt(len(history))}</b></span>'
    f"<span>Expected <b>{fmt(expected)}</b></span></div>"
    "</div></div>",
    unsafe_allow_html=True,
)


# =================================================================
# KPI cards (same component as the Admin Dashboard)
# =================================================================
avg_daily = basis["sum"].mean()
hour_profile = hourly.groupby("hour")["vehicles"].mean()
peak_hour = hour_profile.idxmax()
top_row = history.loc[history["vehicle_count"].idxmax()]

basis_weekday = pd.Series(pd.to_datetime(basis.index).dayofweek, index=basis.index)
week_avg = basis["sum"].groupby(basis_weekday).mean().reindex(range(7))
busiest_wd = int(week_avg.idxmax())
week_max = week_avg.max() or 1
week_bars = (
    '<div class="ct-ha-week">' + "".join(
        f'<span class="{"top" if i == busiest_wd else ""}" '
        f'style="height:{max(8, (v / week_max * 100) if pd.notna(v) else 0):.0f}%" '
        f'title="{WEEKDAY_NAMES[i]}: {fmt(v)} vehicles"></span>'
        for i, v in enumerate(week_avg)
    ) + '</div><div class="ct-ha-week-labels">' + "".join(f"<span>{d[0]}</span>" for d in WEEKDAYS) + "</div>"
)

kpi_grid(
    kpi_card(ICONS["steering-wheel"], "AVG VEHICLES / DAY",
               f'<div class="ct-admin-kpi-value">{fmt(avg_daily)}</div>',
               f"Average of {fmt(len(basis))} days"
               + (" with at least 90% of intervals" if not usable_days.empty else " (all partial)")),
    kpi_card(ICONS["clock"], "PEAK HOUR",
               f'<div class="ct-admin-kpi-value gold">{hour_label(peak_hour)}</div>',
               f"About {fmt(hour_profile.max())} vehicles in that hour on an average day"),
    kpi_card(ICONS["trending-up"], "HIGHEST RECORDED",
               f'<div class="ct-admin-kpi-value">{fmt(top_row["vehicle_count"])}'
               '<span class="ct-unit">/ 15 min</span></div>',
               f'{top_row["datetime"]:%a %d %b %Y} · {clock(top_row["datetime"])}'),
    kpi_card(ICONS["calendar-week"], "BUSIEST DAY OF WEEK",
               f'<div class="ct-admin-kpi-value gold">{WEEKDAY_NAMES[busiest_wd]}</div>{week_bars}',
               f"{fmt(week_avg.max())} vehicles on an average {WEEKDAY_NAMES[busiest_wd]}"),
)
divider()


# =================================================================
# 1. Daily traffic pattern. Not a fragment: the records table at the bottom of the page
#    follows the date picked here, so changing it reruns the page.
# =================================================================
default_day = (max(usable_days.index) if not usable_days.empty else last_ts.date())


def day_explorer(history):
    """Draws the daily pattern panel and returns (day, day_rows) for the records table."""
    with st.container(key="panel_ha_day"):
        st.markdown(
            panel_heading("📅 Daily Traffic Pattern", "Drag to zoom · double-click to reset")
            + '<div class="ct-legend">'
            '<span><i class="gold"></i>Recorded traffic</span>'
            '<span><i class="dot-red"></i>Peak</span></div>',
            unsafe_allow_html=True,
        )
        date_col, range_col, res_col = st.columns([1.2, 2, 1.3], vertical_alignment="center")
        with date_col:
            day = st.date_input(
                "Select date", value=default_day, format="DD/MM/YYYY", label_visibility="collapsed",
                min_value=first_ts.date(), max_value=last_ts.date(), key=f"ha_date_{direction_id}",
            )
        with range_col:
            st.markdown(
                f'<div class="ct-ha-range"><i>◷</i> Data available <b>{first_ts:%d %b %Y}</b> → '
                f"<b>{last_ts:%d %b %Y}</b></div>",
                unsafe_allow_html=True,
            )
        with res_col:
            resolution = st.segmented_control(
                "Resolution", ["Hourly", "15-min"], default="Hourly",
                key="res_ha_day", label_visibility="collapsed",
            ) or "Hourly"

        day_rows = history[history["date"] == day]
        day_start = datetime.combine(day, datetime.min.time())

        if day_rows.empty:
            st.markdown(
                f'<div class="ct-empty"><b>No records for {day:%A, %d %B %Y}</b>'
                "This date is a gap in the telemetry data. Pick another date.</div>",
                unsafe_allow_html=True,
            )
        else:
            # Full day of slots, so missing intervals show as breaks in the line (never filled in).
            counts = day_rows.set_index("datetime")["vehicle_count"]
            if resolution == "Hourly":
                slots = pd.date_range(day_start, periods=24, freq="h")
                series = counts.resample("h").sum(min_count=1).reindex(slots)
                unit = "vehicles / hour"
            else:
                slots = pd.date_range(day_start, periods=INTERVALS_PER_DAY, freq="15min")
                series = counts.reindex(slots)
                unit = "vehicles / 15 min"
            shown = series.dropna()

            peak_ts, peak_val = shown.idxmax(), shown.max()
            quiet_ts, quiet_val = shown.idxmin(), shown.min()
            mean_val = shown.mean()

            fig = go.Figure()
            fig.add_trace(gold_area(
                x=series.index, y=series.values, mode="lines", name="Recorded", connectgaps=False,
                line=dict(color=GOLD, width=3, shape="spline", smoothing=0.6),
                hovertemplate=f"Recorded <b>%{{y:,.0f}}</b> {unit}<extra></extra>",
            ))
            highlight_marker(fig, peak_ts, peak_val, f"Peak · {clock(peak_ts)}", color=RED)
            fig.add_hline(
                y=mean_val, line=dict(color="rgba(148,163,184,.55)", dash="dot", width=1),
                annotation_text=f"Avg {fmt(mean_val)}", annotation_position="top left",
                annotation_font=dict(color="#9fb0c6", size=10),
            )
            chart_layout(fig, 380, unit, dict(
                range=[day_start, day_start + timedelta(days=1)], tickformat="%H:%M",
                dtick=2 * 3600 * 1000, hoverformat="%I:%M %p", **SPIKES,
            ))
            st.plotly_chart(fig, use_container_width=True, config=PLOT_CONFIG)

            st.markdown(
                '<div class="ct-chart-stats">'
                f'<div><span>Total count</span><strong>{fmt(day_rows["vehicle_count"].sum())}</strong><small>vehicles · {day:%a %d %b}</small></div>'
                f'<div><span>Peak time</span><strong class="peak">{clock(peak_ts)}</strong><small>{fmt(peak_val)} {unit}</small></div>'
                f'<div><span>Quietest time</span><strong class="quiet">{clock(quiet_ts)}</strong><small>{fmt(quiet_val)} {unit}</small></div>'
                f'<div><span>Average count</span><strong class="gold">{fmt(mean_val)}</strong><small>{unit}</small></div>'
                "</div>",
                unsafe_allow_html=True,
            )

    return day, day_rows


def records_table(day, day_rows):
    """Every recorded 15-minute interval on the chosen day (bottom of the page)."""
    with st.container(key="panel_ha_table"):
        title_col, dl_col = st.columns([3, 1], vertical_alignment="center")
        with title_col:
            st.markdown(
                f'<div class="ct-head"><div class="ct-section">🗂️ Traffic Records · {day:%a %d %b %Y}</div></div>'
                '<div class="ct-subnote">Every recorded 15-minute interval on this day.</div>',
                unsafe_allow_html=True,
            )
        if day_rows.empty:
            st.info("No records to show for this date.")
            return

        with dl_col:
            st.download_button(
                "⬇ Download CSV",
                data=day_rows[["datetime", "vehicle_count"]].rename(columns={"vehicle_count": "vehicles"})
                .to_csv(index=False).encode("utf-8"),
                file_name=f"traffic_{location_name}_{heading}_{day:%Y-%m-%d}.csv".replace(" ", "_"),
                mime="text/csv", key="ha_download",
            )

        top = float(day_rows["vehicle_count"].max() or 1)
        rows = "".join(
            f'<tr style="--i:{i}"><td>{r.datetime:%H:%M}</td>'
            f'<td><div class="ct-tbar"><div class="ct-meter"><span style="width:{min(100, r.vehicle_count / top * 100):.1f}%"></span></div>'
            f"<b>{fmt(r.vehicle_count)}</b></div></td></tr>"
            for i, r in enumerate(day_rows.itertuples(index=False))
        )
        st.markdown(
            '<div class="ct-table-wrap"><table class="ct-table ct-ha-table"><thead><tr>'
            "<th>TIME</th><th>VEHICLES / 15 MIN</th>"
            f"</tr></thead><tbody>{rows}</tbody></table></div>",
            unsafe_allow_html=True,
        )


day, day_rows = day_explorer(history)
divider()


# =================================================================
# 2. Average traffic by hour of day (all days / weekdays / weekends)
# =================================================================
@st.fragment
def hour_distribution(hourly):
    with st.container(key="panel_ha_hour"):
        st.markdown(
            panel_heading("🕒 Average Traffic by Hour", "Average vehicles in each hour across the whole record"),
            unsafe_allow_html=True,
        )
        group = st.segmented_control(
            "Days", ["All days", "Weekdays", "Weekends"], default="All days",
            key="ha_hour_filter", label_visibility="collapsed",
        ) or "All days"
        subset = hourly
        if group == "Weekdays":
            subset = hourly[hourly["weekday"] < 5]
        elif group == "Weekends":
            subset = hourly[hourly["weekday"] >= 5]

        profile = subset.groupby("hour")["vehicles"].mean().reindex(range(24))
        if profile.dropna().empty:
            st.info("No records for this selection.")
            return
        top, low = int(profile.idxmax()), int(profile.idxmin())

        fig = go.Figure(go.Bar(
            x=[f"{h:02d}:00" for h in profile.index], y=profile.values,
            marker=dict(color=[RED if h == top else GOLD for h in profile.index], line=dict(width=0)),
            opacity=0.9,
            hovertemplate="%{x}<br><b>%{y:,.0f}</b> vehicles on average<extra></extra>",
        ))
        chart_layout(fig, 340, "vehicles / hour", dict(fixedrange=True, dtick=2))
        fig.update_layout(hovermode="closest", bargap=0.22)
        st.plotly_chart(fig, use_container_width=True, config=PLOT_CONFIG)

        day_total = profile.sum()
        daytime = profile.loc[7:18].sum()
        st.markdown(
            '<div class="ct-chart-stats">'
            f'<div><span>Busiest hour</span><strong class="peak">{hour_label(top)}</strong><small>{fmt(profile[top])} vehicles / hour</small></div>'
            f'<div><span>Quietest hour</span><strong class="quiet">{hour_label(low)}</strong><small>{fmt(profile[low])} vehicles / hour</small></div>'
            f'<div><span>Daytime share</span><strong class="gold">{num(daytime / day_total * 100 if day_total else None, 0)}%</strong><small>of daily traffic, 7 AM – 7 PM</small></div>'
            f'<div><span>Average</span><strong>{fmt(profile.mean())}</strong><small>vehicles / hour · {group.lower()}</small></div>'
            "</div>",
            unsafe_allow_html=True,
        )


hour_distribution(hourly)
divider()


# =================================================================
# 3. Daily average trend over the whole period
# =================================================================
@st.fragment
def daily_trend(per_day):
    with st.container(key="panel_ha_trend"):
        st.markdown(
            panel_heading("📈 Daily Average Traffic Trend", "Drag to zoom · double-click to reset")
            + '<div class="ct-legend">'
            '<span><i class="gold"></i>Daily average</span>'
            '<span><i class="dot-red"></i>Busiest day</span></div>',
            unsafe_allow_html=True,
        )
        daily = per_day["mean"].copy()
        daily.index = pd.to_datetime(daily.index)
        busy_day, quiet_day = daily.idxmax(), daily.idxmin()

        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=daily.index, y=daily.values, mode="lines", name="Daily average",
            line=dict(color=GOLD, width=1.8),
            hovertemplate="Daily average <b>%{y:,.1f}</b> / 15 min<extra></extra>",
        ))
        highlight_marker(fig, busy_day, daily.max(), f"Busiest · {busy_day:%d %b}", color=RED)
        chart_layout(fig, 380, "avg vehicles / 15 min", dict(
            tickformat="%b %Y", hoverformat="%a %d %b %Y", **SPIKES,
        ))
        st.plotly_chart(fig, use_container_width=True, config=PLOT_CONFIG)

        # Change between the first and last 30 recorded days.
        change_html = '<strong>—</strong><small>Need 60+ days to compare</small>'
        if len(daily) >= 60:
            first30, last30 = daily.iloc[:30].mean(), daily.iloc[-30:].mean()
            if first30:
                change = (last30 - first30) / first30 * 100
                change_html = (f'<strong class="{"up" if change >= 0 else "down"}">{change:+.0f}%</strong>'
                               "<small>last 30 days vs first 30 days</small>")
        st.markdown(
            '<div class="ct-chart-stats">'
            f'<div><span>Busiest day</span><strong class="peak">{busy_day:%d %b %Y}</strong><small>{num(daily.max())} vehicles / 15 min</small></div>'
            f'<div><span>Quietest day</span><strong class="quiet">{quiet_day:%d %b %Y}</strong><small>{num(daily.min())} vehicles / 15 min</small></div>'
            f'<div><span>Overall average</span><strong>{num(daily.mean())}</strong><small>vehicles / 15 min</small></div>'
            f"<div><span>Long-term change</span>{change_html}</div>"
            "</div>",
            unsafe_allow_html=True,
        )


daily_trend(per_day)
divider()


# =================================================================
# 4. Records table for the date chosen in the Daily Traffic Pattern (bottom of the page)
# =================================================================
records_table(day, day_rows)

st.markdown(FOOTER, unsafe_allow_html=True)
