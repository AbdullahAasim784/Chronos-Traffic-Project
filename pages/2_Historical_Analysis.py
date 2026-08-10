import streamlit as st
import pandas as pd
import plotly.express as px

# Page Settings
st.set_page_config(
    page_title="Historical Analysis",
    page_icon="Assets/Historical_icon.png",
    layout="wide"
)

# Load Data
history = pd.read_csv("Data/Telemetry_complete.csv")
history["datetime"] = pd.to_datetime(history["datetime"])

# Header + CSS
st.markdown("""
<style>
.selectedloc{
    display:inline-block;
    background:#202938;
    border:1px solid #334155;
    border-radius:22px;
    padding:16px 28px;
    color:white;
    font-size:24px;
    font-weight:700;
    margin-top:15px;
}
</style>
""", unsafe_allow_html=True)

header_left, header_right = st.columns([3,2])

with header_right:
    locations = sorted(history["location"].unique())
    location = st.selectbox("Select Location:", locations)

    headings = sorted(history[history["location"] == location]["heading"].unique())
    heading = st.selectbox("Select Direction:", headings)

data = history[
    (history["location"] == location) &
    (history["heading"] == heading)
].copy()

with header_left:
    logo_col, title_col = st.columns([0.5, 5])

    with logo_col:
        st.markdown("<br>", unsafe_allow_html=True)
        st.image("Assets/Historical_icon.png")

    with title_col:
        st.markdown("""
        <h1 style="font-size:46px;font-weight:800;margin-bottom:0;">
        Historical Analysis
        </h1>

        <p style="color:#989b9c;font-size:20px;margin-top:6px;">
        Analysis of Historical patterns from Telemetry dataset.
        </p>
        """, unsafe_allow_html=True)

        st.markdown(f"""
            <div class="selectedloc">
                📍 <b>Location:</b> {location}
                &nbsp;&nbsp;&nbsp;|&nbsp;&nbsp;&nbsp;
                🧭 <b>Direction:</b> {heading}
            </div>
        """,unsafe_allow_html=True)

st.divider()

# History Card CSS
st.markdown("""
<style>
.history-card{
    display:flex;
    justify-content:space-evenly;
    align-items:center;
    background:#1F2937;
    border:1px solid #334155;
    border-radius:20px;
    padding:20px;
}

.history-card:hover{
    border-color:#3B82F6;
    box-shadow:0 0 15px rgba(59,130,246,0.25);
}

.history-item{
    flex:1;
    text-align:center;
}

.history-title{
    font-size:22px;
    font-weight:700;
    color:#F8FAFC;
    margin-bottom:12px;
}

.history-value{
    font-size:28px;
    font-weight:700;
    color:#FACC15;
}

.history-divider{
    width:2px;
    height:70px;
    background:#475569;
}
</style>
""", unsafe_allow_html=True)

# Summary Overview
hourly_avg = data.groupby(data["datetime"].dt.hour)["vehicle_count"].mean()
peak_hour = hourly_avg.idxmax()

st.markdown(f"""
    <div class="history-card">

    <div class="history-item">
        <div class="history-title">Total Records</div>
        <div class="history-value">{len(data):,}</div>
    </div>

    <div class="history-divider"></div>

    <div class="history-item">
        <div class="history-title">Average Vehicles</div>
        <div class="history-value">{round(data["vehicle_count"].mean())}</div>
    </div>

    <div class="history-divider"></div>

    <div class="history-item">
        <div class="history-title">Maximum Vehicles</div>
        <div class="history-value">{int(data["vehicle_count"].max())}</div>
    </div>

    <div class="history-divider"></div>

    <div class="history-item">
        <div class="history-title">Peak Hour</div>
        <div class="history-value">{peak_hour:02d}:00 - {peak_hour + 1:02d}:00</div>
    </div>

    </div>
""", unsafe_allow_html=True)

st.divider()

# Historical Traffic Records
st.subheader("Historical Traffic Records")
st.markdown("""
<div style="font-size:16px;color:#989b9c;"
<p>Select a date to view the complete 24-hour traffic records for the selected location and direction.</p>
</div>
""", unsafe_allow_html=True)

min_date = data["datetime"].dt.date.min()
max_date = data["datetime"].dt.date.max()

left, right = st.columns([1,3])

with left:
    selected_date = st.date_input(
        "Select Date",
        value=max_date,
        min_value=min_date,
        max_value=max_date,
    )

with right:
    st.markdown(f"""
    <div style="
        width:420px;
        margin-left:auto;
        background:#1E293B;
        border:1px solid #334155;
        border-radius:10px;
        padding:12px 16px;
        color:#E2E8F0;
        font-size:15px;
        text-align:center;
    ">
        📅 <b>Dates available from: {min_date.strftime('%d %b %Y')} → {max_date.strftime('%d %b %Y')}</b>
    </div>
    """, unsafe_allow_html=True)

day_data = data[data["datetime"].dt.date == selected_date].copy()

if day_data.empty:
    st.warning("No historical records available for the selected date.")

else:
    table = day_data[["datetime", "vehicle_count"]].copy()

    table["datetime"] = table["datetime"].dt.strftime("%H:%M")
    table.columns = ["Time", "Vehicle Count"]

    table = (
        table.style
        .hide(axis="index")
        .set_properties(**{
            "text-align":"center",
            "font-size":"15px"
        })
        .set_table_styles([
            {
                "selector":"th",
                "props":[
                    ("text-align","center"),
                    ("font-size","16px"),
                    ("font-weight","700"),
                    ("background-color","#1E293B"),
                    ("color","white")
                ]
            }
        ])
    )

    with st.container(border=True):
        st.dataframe(table, use_container_width=True, height=350)

    st.markdown("### 📈 Traffic Pattern")

    fig1 = px.line(
        day_data,
        x="datetime",
        y="vehicle_count",
        markers=True,
        title=f"Traffic Volume - {selected_date.strftime('%d %B %Y')}",
        color_discrete_sequence=["#60A5FA"]
    )

    fig1.update_traces(line_width=4, marker_size=7)

    fig1.update_layout(
        height=420,
        plot_bgcolor="#111827",
        paper_bgcolor="#111827",
        hovermode="x unified",
        xaxis_title="Time",
        yaxis_title="Vehicle Count",
        margin=dict(l=20, r=20, t=45, b=20),
        font=dict(color="#E5E7EB",size=14,),
    )

    st.plotly_chart(fig1, use_container_width=True)

st.divider()

# Average Traffic By Hour
st.subheader("Average Traffic Distribution by Hour")
st.markdown("""
<div style="font-size:16px;color:#989b9c;"
<p>Average vehicle count for each hour calculated from the complete historical dataset.</p>
</div>
""", unsafe_allow_html=True)

data["hour"] = (data["datetime"].dt.hour)

hourly_average = (
    data
    .groupby("hour")["vehicle_count"]
    .mean()
    .reset_index()
)

fig2 = px.bar(
    hourly_average,
    x="hour",
    y="vehicle_count",
    title="Average Vehicles Per Hour",
    color_discrete_sequence=["#60A5FA"]
)

fig2.update_layout(
    height=420,
    plot_bgcolor="#111827",
    paper_bgcolor="#111827",
    hovermode="x unified",
    xaxis_title="Hour of Day",
    yaxis_title="Average Vehicle Count",
    font=dict(color="#E5E7EB",size=14,)
)

fig2.update_xaxes(tickmode="linear",tick0=0,dtick=1)

st.plotly_chart(fig2,use_container_width=True)

st.divider()

# Daily Traffic Trend
st.subheader("Daily Average Traffic Trend")
st.markdown("""
<div style="font-size:16px;color:#989b9c;"
<p>Daily average traffic behaviour across the complete historical period.</p>
</div>
""", unsafe_allow_html=True)

data["date"] = (data["datetime"].dt.date)

daily_average = (
    data
    .groupby("date")["vehicle_count"]
    .mean()
    .reset_index()
)

fig3 = px.line(
    daily_average,
    x="date",
    y="vehicle_count",
    title="Daily Average Vehicle Count",
    color_discrete_sequence=["#60A5FA"],
    markers=True
)

fig3.update_traces(line_width=3)

fig3.update_layout(
    height=420,
    plot_bgcolor="#111827",
    paper_bgcolor="#111827",
    hovermode="x unified",
    xaxis_title="Date",
    yaxis_title="Average Vehicle Count",
    margin=dict(l=20,r=20,t=40,b=20),
    font=dict(color="#E5E7EB",size=14,)
)

st.plotly_chart(fig3,use_container_width=True)

st.divider()

st.caption("© 2026 Chronos-Traffic | Bahria University Karachi Campus | Final Year Project Prototype")

# Sidebar
with st.sidebar:
    st.markdown("<br><br><br><br><br><br>", unsafe_allow_html=True)

    st.markdown("""
    <div style=" text-align:center; color:#94A3B8; line-height:1.2;">

    <div style="
        font-size:18px;
        color:white;
        font-weight:700;
        margin-top:10px;
        margin-bottom:5px;">
        🚦 Chronos-Traffic
    </div>

    <div style="font-size:14px; margin-bottom:10px;">
        AI-Driven Spatio-Temporal <br>
        Traffic Forecasting & Anomaly Detection
    </div>

    <div style="
        display:inline-block;
        background:#1F2937;
        border:1px solid #334155;
        border-radius:12px;
        padding:8px 18px;
        color:#60A5FA;
        font-weight:600;
        font-size:14px;
        margin-bottom:10px;">
        Version 1.0
    </div>

    <div style="font-size:13px;">
        © 2026 Bahria University<br>
        Computer Science Department
    </div>

    </div>
    """, unsafe_allow_html=True)