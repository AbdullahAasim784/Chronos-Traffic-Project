"""Chronos-Traffic | Model Performance (admin page).

How well the stored Prophet forecasts matched the traffic that was actually recorded.
Reads SQLite directly (same as the Admin Dashboard), so it works when FastAPI is down.
Tables used: model_metrics (MAE / RMSE / R2) and forecast_validation (timestamp-level rows).
"""
import html
import sqlite3
from datetime import datetime, timedelta

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from utils.admin_ui import (
    admin_header, divider, footer_and_stop, kpi_card, kpi_grid, meter,
    panel_heading, read_sql, route_selectors, setup_admin_page,
)
from utils.forecast_ui import fmt
from utils.ui import BLUE, FOOTER, GOLD, ICONS, PLOT_CONFIG, RED, SKY, SPIKES, chart_layout, highlight_marker

setup_admin_page("Model Performance", "🎯", "model_performance.css")

ACTUAL = GOLD                                # actual (recorded) counts
PREDICT = BLUE                               # predicted counts, so the two lines contrast
BAND_FILL = "rgba(96,165,250,0.14)"          # confidence interval belongs to the prediction


def num(value, digits=2):
    """Decimal formatting; fmt() from forecast_ui rounds to whole numbers."""
    if value is None or pd.isna(value):
        return "—"
    return f"{value:,.{digits}f}"


admin_header("Model Performance", "Prophet forecasts evaluated against recorded traffic")
dataset, location, direction = route_selectors("mp", "EVALUATION OVERVIEW")
dataset_id, direction_id = int(dataset["dataset_id"]), int(direction["direction_id"])
dataset_name, location_name, heading = dataset["dataset_name"], location["location_name"], direction["heading"]


# =================================================================
# Load metrics and validation rows for the selected direction
# =================================================================
try:
    metrics = read_sql(
        "SELECT evaluation_type, evaluation_start, evaluation_end, actual_records, matched_records, "
        "mae, rmse, r2_score FROM model_metrics WHERE direction_id = ? ORDER BY evaluation_type",
        (direction_id,),
    )
except sqlite3.Error as exc:
    st.error(f"Model metrics unavailable: {exc}")
    footer_and_stop()

if metrics.empty:
    st.info("No evaluation results are stored for this road and direction yet.")
    footer_and_stop()

eval_types = metrics["evaluation_type"].tolist()
if len(eval_types) > 1:
    chosen = st.segmented_control(
        "Evaluation", eval_types, default=eval_types[0], key="mp_eval_type", label_visibility="collapsed",
    ) or eval_types[0]
else:
    chosen = eval_types[0]
metric = metrics[metrics["evaluation_type"] == chosen].iloc[0]

try:
    validation = read_sql(
        "SELECT datetime, actual, predicted, min_predicted, max_predicted, error, absolute_error, status "
        "FROM forecast_validation WHERE direction_id = ? AND evaluation_type = ? ORDER BY datetime",
        (direction_id, chosen),
    ).copy()
except sqlite3.Error as exc:
    st.error(f"Validation rows unavailable: {exc}")
    footer_and_stop()

if validation.empty:
    st.info("No timestamp-level validation rows are stored for this road and direction.")
    footer_and_stop()

validation["datetime"] = pd.to_datetime(validation["datetime"], errors="coerce")
NUMBER_COLS = ["actual", "predicted", "min_predicted", "max_predicted", "error", "absolute_error"]
validation[NUMBER_COLS] = validation[NUMBER_COLS].apply(pd.to_numeric, errors="coerce")
validation = validation.dropna(subset=["datetime"])
validation["in_band"] = validation["actual"].between(validation["min_predicted"], validation["max_predicted"])
validation["date"] = validation["datetime"].dt.date
scored = validation.dropna(subset=["actual", "predicted"])     # rows with both values

coverage = scored["in_band"].mean() * 100 if not scored.empty else None
bias = scored["error"].mean() if not scored.empty else None    # error = actual − predicted


# =================================================================
# Evaluation summary: short paragraph + match-rate meter
# =================================================================
start = pd.to_datetime(metric["evaluation_start"]) if pd.notna(metric["evaluation_start"]) else validation["datetime"].min()
end = pd.to_datetime(metric["evaluation_end"]) if pd.notna(metric["evaluation_end"]) else validation["datetime"].max()
n_days = scored["date"].nunique()
actual_records = metric["actual_records"]
matched_records = metric["matched_records"]
match_rate = (matched_records / actual_records * 100) if pd.notna(actual_records) and actual_records else None

if bias is None:
    bias_sentence = ""
elif abs(bias) < 0.5:
    bias_sentence = " On average its predictions are <strong>almost unbiased</strong>."
else:
    word = "over-predicts" if bias < 0 else "under-predicts"
    bias_sentence = (f' On average the model <span class="ct-hl blue">{word}</span> by '
                     f"<strong>{abs(bias):.1f} vehicles</strong> per 15 minutes.")

st.markdown(
    '<div class="ct-summary"><div>'
    '<div class="ct-admin-eyebrow">EVALUATION SUMMARY</div>'
    f"<p>Prophet was tested on <strong>{n_days} day{'s' if n_days != 1 else ''}</strong> of recorded traffic, "
    f'from <span class="ct-hl">{start:%d %b}</span> to <span class="ct-hl">{end:%d %b %Y}</span>. '
    f"Of <strong>{fmt(actual_records)}</strong> observed 15-minute intervals, "
    f"<strong>{fmt(matched_records)}</strong> had a forecast at the same timestamp, which gives a "
    f'<span class="ct-hl">{num(match_rate, 1)}% match rate</span>.{bias_sentence}</p>'
    "</div>"
    '<div class="ct-summary-side">'
    '<div class="ct-summary-top"><span class="ct-summary-label">MATCH RATE</span>'
    f'<span class="ct-summary-value">{num(match_rate, 1)}%</span></div>'
    f"{meter(match_rate)}"
    f'<div class="ct-summary-legend"><span>Matched <b>{fmt(matched_records)}</b></span>'
    f"<span>Observed <b>{fmt(actual_records)}</b></span></div>"
    "</div></div>",
    unsafe_allow_html=True,
)


# =================================================================
# Error-metric KPI cards (same component as the Admin Dashboard)
# =================================================================
r2 = metric["r2_score"]
r2_pct = r2 * 100 if pd.notna(r2) else None
mae, rmse = metric["mae"], metric["rmse"]
ratio_note = f" · RMSE/MAE ratio {rmse / mae:.2f}" if pd.notna(mae) and pd.notna(rmse) and mae else ""

kpi_grid(
    kpi_card(ICONS["ruler"], "MAE",
               f'<div class="ct-admin-kpi-value">{num(mae)}<span class="ct-unit">vehicles</span></div>',
               "Mean absolute error · average miss per 15-minute interval"),
    kpi_card(ICONS["function"], "RMSE",
               f'<div class="ct-admin-kpi-value">{num(rmse)}<span class="ct-unit">vehicles</span></div>',
               "Root mean squared error · weighs large misses more" + ratio_note),
    kpi_card(ICONS["target"], "R² SCORE",
               f'<div class="ct-admin-kpi-value gold">{num(r2, 3)}</div>{meter(r2_pct)}',
               f"Explains {num(r2_pct, 0)}% of the variation in recorded traffic"),
    kpi_card(ICONS["shield"], "INTERVAL COVERAGE",
               f'<div class="ct-admin-kpi-value">{num(coverage, 1)}%</div>{meter(coverage, blue=True)}',
               "Recorded counts that fell inside the confidence interval"),
)
divider()


# =================================================================
# Actual vs Predicted chart. A fragment: changing day or resolution reruns only the chart.
# =================================================================
def day_label(day):
    return f"{day:%a %d}"


@st.fragment
def comparison_chart(validation):
    days = sorted(validation["date"].unique())
    options = ["All days"] + [day_label(d) for d in days]

    with st.container(key="panel_mp_chart"):
        st.markdown(
            panel_heading("📈 Actual vs Predicted Traffic", "Drag to zoom · double-click to reset")
            + '<div class="ct-legend">'
            '<span><i class="gold"></i>Actual (recorded)</span>'
            '<span><i class="blue"></i>Predicted (Prophet)</span>'
            '<span><i class="band"></i>Confidence interval</span>'
            '<span><i class="dot-red"></i>Largest gap</span></div>',
            unsafe_allow_html=True,
        )
        day_col, res_col = st.columns([4, 1.3], vertical_alignment="center")
        with day_col:
            choice = st.segmented_control(
                "Validation day", options, default="All days",
                key="mp_graph_day", label_visibility="collapsed",
            ) or "All days"
        with res_col:
            resolution = st.segmented_control(
                "Resolution", ["Hourly", "15-min"], default="Hourly",
                key="res_mp_chart", label_visibility="collapsed",
            ) or "Hourly"

        if choice == "All days":
            data = validation
        else:
            data = validation[validation["date"] == days[options.index(choice) - 1]]

        frame = data.set_index("datetime")[["actual", "predicted", "min_predicted", "max_predicted"]]
        if resolution == "Hourly":
            frame = frame.resample("h").sum(min_count=1)
            unit = "vehicles / hour"
        else:
            unit = "vehicles / 15 min"
        frame = frame.dropna(how="all")

        if frame.empty:
            st.info("No validation rows for this selection.")
            return

        fig = go.Figure()
        # Confidence band first, so the lines draw on top of it.
        fig.add_trace(go.Scatter(
            x=frame.index, y=frame["max_predicted"], mode="lines",
            line=dict(width=0, shape="spline", smoothing=0.6), hoverinfo="skip",
        ))
        fig.add_trace(go.Scatter(
            x=frame.index, y=frame["min_predicted"], mode="lines",
            line=dict(width=0, shape="spline", smoothing=0.6),
            fill="tonexty", fillcolor=BAND_FILL, hoverinfo="skip",
        ))
        fig.add_trace(go.Scatter(
            x=frame.index, y=frame["actual"], mode="lines", name="Actual",
            line=dict(color=ACTUAL, width=3, shape="spline", smoothing=0.6),
            hovertemplate=f"Actual <b>%{{y:,.0f}}</b> {unit}<extra></extra>",
        ))
        fig.add_trace(go.Scatter(
            x=frame.index, y=frame["predicted"], mode="lines", name="Predicted",
            line=dict(color=PREDICT, width=2.6, shape="spline", smoothing=0.6),
            customdata=frame[["min_predicted", "max_predicted"]].to_numpy(),
            hovertemplate=("Predicted <b>%{y:,.0f}</b> "
                           "<span style='color:#9fb0c6'>(range %{customdata[0]:,.0f}–%{customdata[1]:,.0f})</span>"
                           "<extra></extra>"),
        ))

        # Largest gap between the two lines in the current view.
        gap = (frame["actual"] - frame["predicted"]).abs().dropna()
        if not gap.empty:
            miss_ts = gap.idxmax()
            highlight_marker(fig, miss_ts, frame.loc[miss_ts, "actual"], f"Largest gap · {gap.max():,.0f}", color=RED)

        if choice == "All days":
            x_axis = dict(tickformat="%a %d %b", dtick=24 * 3600 * 1000, hoverformat="%a %d %b · %I:%M %p")
        else:
            day_start = datetime.combine(days[options.index(choice) - 1], datetime.min.time())
            x_axis = dict(range=[day_start, day_start + timedelta(days=1)], tickformat="%H:%M",
                          dtick=2 * 3600 * 1000, hoverformat="%I:%M %p")
        x_axis.update(SPIKES)
        chart_layout(fig, 400, unit, x_axis)
        st.plotly_chart(fig, use_container_width=True, config=PLOT_CONFIG)


comparison_chart(validation)


# =================================================================
# Error analysis: by hour of day + error distribution
# =================================================================
divider()
with st.container(key="panel_mp_error"):
    st.markdown(
        panel_heading("🔍 Error Analysis", "Where and how the model misses"),
        unsafe_allow_html=True,
    )
    hour_col, dist_col = st.columns(2, gap="large")

    with hour_col:
        hourly = scored.groupby(scored["datetime"].dt.hour)["absolute_error"].mean()
        worst_hour = hourly.idxmax() if not hourly.empty else None
        st.markdown(
            '<div class="ct-subhead">ERROR BY HOUR OF DAY</div>'
            '<div class="ct-subnote">Average absolute error for each hour'
            + (f' · hardest hour <b class="ct-hl blue">{worst_hour:02d}:00</b>' if worst_hour is not None else "")
            + "</div>",
            unsafe_allow_html=True,
        )
        hour_fig = go.Figure(go.Bar(
            x=[f"{h:02d}:00" for h in hourly.index], y=hourly.values,
            marker=dict(color=[PREDICT if h == worst_hour else ACTUAL for h in hourly.index],
                        line=dict(width=0)),
            opacity=0.9,
            hovertemplate="%{x}<br><b>%{y:,.1f}</b> vehicles off on average<extra></extra>",
        ))
        chart_layout(hour_fig, 300, "Mean absolute error", dict(dtick=3, fixedrange=True))
        hour_fig.update_layout(hovermode="closest", bargap=0.25)
        st.plotly_chart(hour_fig, use_container_width=True, config=PLOT_CONFIG)

    with dist_col:
        st.markdown(
            '<div class="ct-subhead">ERROR DISTRIBUTION</div>'
            '<div class="ct-subnote">Actual − predicted · left of 0 means the model predicted too high</div>',
            unsafe_allow_html=True,
        )
        dist_fig = go.Figure(go.Histogram(
            x=scored["error"], nbinsx=30, marker=dict(color=SKY, line=dict(width=0)), opacity=0.85,
            hovertemplate="Error %{x}<br><b>%{y}</b> intervals<extra></extra>",
        ))
        dist_fig.add_shape(type="line", x0=0, x1=0, y0=0, y1=1, yref="paper",
                           line=dict(color="rgba(245,189,87,.7)", dash="dot", width=1))
        chart_layout(dist_fig, 300, "Number of intervals", dict(fixedrange=True))
        dist_fig.update_layout(hovermode="closest", bargap=0.06)
        st.plotly_chart(dist_fig, use_container_width=True, config=PLOT_CONFIG)


# =================================================================
# Validation records table. A fragment: changing the day reruns only the table.
# =================================================================
@st.fragment
def validation_table(validation):
    days = sorted(validation["date"].unique())
    options = ["All days"] + [day_label(d) for d in days]

    with st.container(key="panel_mp_table"):
        st.markdown(
            panel_heading("🗂️ Validation Records", "Every 15-minute interval from the forecast_validation table"),
            unsafe_allow_html=True,
        )
        choice = st.segmented_control(
            "Table day", options, default="All days", key="mp_table_day", label_visibility="collapsed",
        ) or "All days"
        view = validation if choice == "All days" else validation[validation["date"] == days[options.index(choice) - 1]]
        if view.empty:
            st.info("No validation rows for this selection.")
            return

        time_fmt = "%a %d %b · %H:%M" if choice == "All days" else "%H:%M"
        max_abs = float(validation["absolute_error"].max() or 1)
        rows = []
        for i, r in enumerate(view.itertuples(index=False)):
            width = 0 if pd.isna(r.absolute_error) else min(100, r.absolute_error / max_abs * 100)
            err_cls = "" if pd.isna(r.error) or r.error == 0 else ("over" if r.error < 0 else "under")
            rows.append(
                f'<tr style="--i:{i}"><td>{r.datetime:{time_fmt}}</td>'
                f"<td>{fmt(r.actual)}</td><td>{fmt(r.predicted)}</td>"
                f"<td>{fmt(r.min_predicted)}</td><td>{fmt(r.max_predicted)}</td>"
                f'<td class="{err_cls}">{fmt(r.error)}</td>'
                f'<td><div class="ct-tbar"><div class="ct-meter"><span style="width:{width:.1f}%"></span></div>'
                f"<b>{fmt(r.absolute_error)}</b></div></td></tr>"
            )
        st.markdown(
            '<div class="ct-table-wrap"><table class="ct-table ct-mp-vtable"><thead><tr>'
            "<th>TIME</th><th>ACTUAL</th><th>PREDICTED</th><th>LOWER BOUND</th><th>UPPER BOUND</th>"
            '<th title="Actual − Predicted">ERROR</th><th>ABSOLUTE ERROR</th>'
            f"</tr></thead><tbody>{''.join(rows)}</tbody></table></div>"
            '<div class="ct-mp-table-note">Error = actual − predicted · '
            '<span class="over">negative</span> = predicted too high · '
            '<span class="under">positive</span> = predicted too low</div>',
            unsafe_allow_html=True,
        )


divider()
validation_table(validation)


# =================================================================
# Location comparison: every direction in the dataset, ranked by MAE
# =================================================================
divider()
try:
    summary = read_sql(
        """SELECT ld.direction_id, l.location_name, ld.heading,
                  m.mae, m.rmse, m.r2_score, m.matched_records
           FROM model_metrics m
           JOIN location_directions ld ON ld.direction_id = m.direction_id
           JOIN locations l ON l.location_id = ld.location_id
           WHERE l.dataset_id = ? AND m.evaluation_type = ?
           ORDER BY m.mae""",
        (dataset_id, chosen),
    )
except sqlite3.Error:
    summary = pd.DataFrame()

with st.container(key="panel_mp_compare"):
    st.markdown(
        panel_heading("🏁 Location Comparison", f"{html.escape(str(dataset_name))} · ranked by MAE, lower is better"),
        unsafe_allow_html=True,
    )
    if summary.empty:
        st.info("No metrics available for other locations in this dataset.")
    else:
        summary = summary.reset_index(drop=True)
        position = summary.index[summary["direction_id"] == direction_id]
        if len(position):
            st.markdown(
                f'<div class="ct-mp-callout"><strong>{html.escape(str(location_name))} · {html.escape(str(heading))}</strong> '
                f'ranks <span class="ct-hl">#{position[0] + 1}</span> of {len(summary)} directions in this dataset.</div>',
                unsafe_allow_html=True,
            )
        body = "".join(
            f'<tr class="{"is-current" if r.direction_id == direction_id else ""}" style="--i:{i}">'
            f'<td><span class="ct-mp-rank">{i + 1}</span></td>'
            f"<td>{html.escape(str(r.location_name))}"
            + ('<span class="ct-mp-you">YOU</span>' if r.direction_id == direction_id else "")
            + f"</td><td>{html.escape(str(r.heading))}</td>"
            f"<td>{num(r.mae)}</td><td>{num(r.rmse)}</td>"
            f'<td><div class="ct-mp-r2">{meter(r.r2_score * 100 if pd.notna(r.r2_score) else 0)}'
            f"<b>{num(r.r2_score, 3)}</b></div></td>"
            f"<td>{fmt(r.matched_records)}</td></tr>"
            for i, r in enumerate(summary.itertuples(index=False))
        )
        st.markdown(
            '<div class="ct-table-wrap"><table class="ct-table"><thead><tr>'
            "<th>RANK</th><th>LOCATION</th><th>DIRECTION</th><th>MAE</th><th>RMSE</th><th>R²</th><th>MATCHED</th>"
            f"</tr></thead><tbody>{body}</tbody></table></div>",
            unsafe_allow_html=True,
        )

st.markdown(FOOTER, unsafe_allow_html=True)
