import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import folium
import plotly.express as px
from streamlit_folium import st_folium

# Page Settings
st.set_page_config(
    page_title="Dashboard",
    page_icon= "Assets/Dashboard_icon.png",
    layout="wide"
)

# Load Datasets
history = pd.read_csv("Data/Telemetry_complete.csv")
forecast = pd.read_csv("Data/Telemetry_Forecast.csv")

history["datetime"] = pd.to_datetime(history["datetime"])
forecast["datetime"] = pd.to_datetime(forecast["datetime"])

#Header
header_left, header_right = st.columns([3,2])

# Header CSS
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
}

.time-card{
    background:#202938;
    border:1px solid #334155;
    border-radius:18px;
    padding:16px 24px;
    text-align:center;
    color:#60A5FA;
    font-size:20px;
    font-weight:700;
    width:100%;
}
</style>
""", unsafe_allow_html=True)

with header_left:
    logo_col, title_col = st.columns([0.5, 5])

    with logo_col:
        st.markdown("<br>", unsafe_allow_html=True)
        st.image("Assets/Dashboard_icon.png")

    with title_col:
        st.markdown("""
        <h1 style="font-size:46px;font-weight:800;margin-bottom:0;">
        Traffic Dashboard
        </h1>

        <p style="color:#989b9c;font-size:20px;margin-top:6px;">
        Real-Time Traffic Forecasting and Congestion Monitoring
        </p>
        """, unsafe_allow_html=True)

with header_right:
    locations = sorted(forecast["location"].unique())
    location = st.selectbox("Select Location:", locations)

    headings = sorted(forecast[forecast["location"] == location]["heading"].unique())
    heading = st.selectbox("Select Direction:", headings)

current_time = datetime.now().strftime("%d %b %Y | %I:%M:%S %p")

left, right = st.columns([3.5, 1.5])

with left:
    st.markdown(f"""
    <div class="selectedloc">
        📍 <b>Location:</b> {location}
        &nbsp;&nbsp;&nbsp;|&nbsp;&nbsp;&nbsp;
        🧭 <b>Direction:</b> {heading}
    </div>
    """, unsafe_allow_html=True)

with right:
    st.markdown(f"""
    <div class="time-card">
        🕒 {current_time}
    </div>
    """, unsafe_allow_html=True)

st.divider()

# Next 15-Minute Prediction
now = datetime.now()
minute = ((now.minute // 15) + 1) * 15

if minute == 60:
    forecast_time = now.replace(
        minute=0,
        second=0,
        microsecond=0
    ) + timedelta(hours=1)
else:
    forecast_time = now.replace(
        minute=minute,
        second=0,
        microsecond=0
    )

# Filter Selected Route
selected = forecast[(forecast["location"] == location) & (forecast["heading"] == heading)].copy()
selected["time"] = selected["datetime"].dt.strftime("%H:%M")
prediction = selected[selected["time"] == forecast_time.strftime("%H:%M")]

# Prediction Card CSS
st.markdown("""
<style>
.pred-card{
    display:flex;
    justify-content:space-around;
    align-items:center;
    background:#1F2937;
    border:1px solid #334155;
    border-radius:20px;
    padding:20px;
}

.pred-card:hover{
    border-color:#3B82F6;
    box-shadow:0 0 15px rgba(59,130,246,0.25);
}

.pred-item{
    flex:1;
    text-align:center;
}

.pred-title{
    font-size:22px;
    font-weight:700;
    color:#F8FAFC;
    margin-bottom:12px;
}

.pred-value{
    font-size:28px;
    font-weight:700;
    color:#FACC15;
}

.pred-divider{
    width:2px;
    height:90px;
    background:#475569;
}
</style>
""", unsafe_allow_html=True)

if not prediction.empty:

    row = prediction.iloc[0]
    # Prediction Card Classes
    st.markdown(f"""
    <div class="pred-card">
        <div class="pred-item">
            <div class="pred-title">Forecast Time</div>
            <div class="pred-value">{forecast_time.strftime("%I:%M %p")}</div>
        </div>
        <div class="pred-divider"></div>
        <div class="pred-item">
            <div class="pred-title">Vehicle Count</div>
            <div class="pred-value">{int(row["vehicle_count"])} Vehicles</div>
        </div>
        <div class="pred-divider"></div>
        <div class="pred-item">
            <div class="pred-title">Congestion</div>
            <div class="pred-value">{row["congestion"]}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

else:
    st.warning("No prediction available.")

st.divider()

# Main Container
st.markdown("""
<style>
.forecast-card{
    background:#1B2433;
    border:1px solid #365B94;
    border-radius:18px;
    padding:22px;
    margin-bottom:22px;
}

.forecast-card:hover{
    border-color:#60A5FA;
    box-shadow:0 0 18px rgba(59,130,246,.35);
}

.forecast-title{
    color:#FACC15;
    font-size:20px;
    font-weight:700;
    margin-bottom:22px;
}

.forecast-text{
    color:#D1D5DB;
    font-size:17px;
    line-height:2;
}

.forecast-value{
    color:#60A5FA;
    font-weight:700;
}

</style>
""", unsafe_allow_html=True)

left, divider, right = st.columns([3.2,0.03,2])

# Left: Traffic RoadMap
with left:
    st.subheader("🗺️ Traffic Roadmap")
    with st.container(border=True):
        if not prediction.empty:

            row = prediction.iloc[0]

            lat = float(row["latitude"])
            lon = float(row["longitude"])

            traffic = row["congestion"]

            if traffic == "Low":
                border="#16A34A"
                fill="#4ADE80"

            elif traffic=="Medium":
                border="#F59E0B"
                fill="#FCD34D"

            else:
                border="#DC2626"
                fill="#F87171"

            m = folium.Map(
                location=[lat,lon],
                zoom_start=14,
                scrollWheelZoom=False
            )

            folium.CircleMarker(
                location=[lat,lon],
                radius=32,
                color=border,
                weight=4,
                fill=True,
                fill_color=fill,
                fill_opacity=.5,
                popup=f"""
                <b>Location:</b> {location}<br>
                <b>Direction:</b> {heading}<br>
                <b>Forecast:</b> {int(row["vehicle_count"])} Vehicles<br>
                <b>Congestion:</b> {traffic}
                """
            ).add_to(m)

            st_folium(
                m,
                height=430,
                width=None,
            )

        else:
            st.warning("No prediction available.")

with divider:
    st.markdown("""
    <div style="
        border-left:2px solid #3B4456;
        height:550px;
        margin:auto;
    "></div>
""", unsafe_allow_html=True)

# Right: Upcoming Forecasts
with right:
    st.subheader("📅 Upcoming Forecasts")
    st.markdown('<div class="forecast-box">', unsafe_allow_html=True)

    # 30 Minutes
    time30 = forecast_time + timedelta(minutes=30)
    pred30 = selected[selected["time"] == time30.strftime("%H:%M")]

    if not pred30.empty:
        row30 = pred30.iloc[0]
        st.markdown(f"""
        <div class="forecast-card">
        <div class="forecast-title">
        ⏱ Next 30 Minutes
        </div>

        <div class="forecast-text">
        Vehicle Count:
        <span class="forecast-value"> 
        {int(row30['vehicle_count'])} Vehicles 
        </span>
        </div>

        <div class="forecast-text">
        Congestion: 
        <span class="forecast-value"> 
        {row30['congestion']} 
        </span>
        </div>

        <div class="forecast-text">
        Forecast Time:
        <span class="forecast-value"> 
        {time30.strftime('%I:%M %p')} 
        </span>
        </div>
        </div>
""", unsafe_allow_html=True)

    # 60 Minutes
    time60 = forecast_time + timedelta(minutes=60)
    pred60 = selected[selected["time"] == time60.strftime("%H:%M")]

    if not pred60.empty:
        row60 = pred60.iloc[0]
        st.markdown(f"""
        <div class="forecast-card">
        <div class="forecast-title">
        ⏱ Next 60 Minutes
        </div>

        <div class="forecast-text">
        Vehicle Count:
        <span class="forecast-value"> 
        {int(row60['vehicle_count'])} Vehicles 
        </span>
        </div>

        <div class="forecast-text">
        Congestion: 
        <span class="forecast-value"> 
        {row60['congestion']} 
        </span>
        </div>

        <div class="forecast-text">
        Forecast Time:
        <span class="forecast-value"> 
        {time60.strftime('%I:%M %p')} 
        </span>
        </div>
        </div>
""", unsafe_allow_html=True)

st.divider()

# Traffic Forecast Trend
st.subheader("📈 Traffic Forecast Trend")
st.caption("🔵 Historical Average Traffic   |   🟠 Prophet Forecast   |   🟡 Current Prediction")

history_selected = history[
    (history["location"] == location) &
    (history["heading"] == heading)
].copy()

history_selected["time"] = history_selected["datetime"].dt.strftime("%H:%M")

historical_avg = (
    history_selected
    .groupby("time")["vehicle_count"]
    .mean()
    .reset_index()
)

historical_avg.rename(columns={"vehicle_count": "Historical"},inplace=True)

forecast_selected = forecast[
    (forecast["location"] == location) &
    (forecast["heading"] == heading)
].copy()

forecast_selected["time"] = forecast_selected["datetime"].dt.strftime("%H:%M")

forecast_selected = forecast_selected[["time", "vehicle_count"]].rename(columns={"vehicle_count": "Forecast"})

trend = historical_avg.merge(forecast_selected, on="time", how="inner")

fig = px.line(
    trend,
    x="time",
    y=["Historical", "Forecast"],
    color_discrete_map={"Historical": "#3B82F6","Forecast": "#F97316"},
)

# Current Prediction Marker
selected_time = forecast_time.strftime("%H:%M")
selected_point = trend[trend["time"] == selected_time]

if not selected_point.empty:
    fig.add_scatter(
        x=selected_point["time"],
        y=selected_point["Forecast"],
        mode="markers",
        marker=dict(size=16,color="#FACC15",line=dict(color="#F97316", width=3)),
        name="Current Prediction",
    )

fig.update_traces(line=dict(width=4),)

# Layout
fig.update_layout(
    height=420,
    plot_bgcolor="#111827",
    paper_bgcolor="#111827",
    hovermode="x unified",
    margin=dict(l=20, r=20, t=20, b=20,),
    font=dict(color="#E5E7EB",size=14,),
    legend=dict(orientation="h",y=1.08,x=0,bgcolor="rgba(0,0,0,0)",font=dict(size=13),),
    xaxis_title="Time of Day",
    yaxis_title="Vehicle Count",
)

fig.update_xaxes(
    tickangle=-45,
    nticks=24,
    showgrid=False,
    showline=True,
    linecolor="#374151",
    tickfont=dict(color="#D1D5DB"),
)

fig.update_yaxes(
    showgrid=True,
    gridcolor="#374151",
    zeroline=False,
    showline=True,
    linecolor="#374151",
    tickfont=dict(color="#D1D5DB"),
)

st.plotly_chart(fig, use_container_width=True)

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