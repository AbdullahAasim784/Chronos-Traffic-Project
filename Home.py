import streamlit as st
import pandas as pd

# Pag Settings
st.set_page_config(
    page_title="Chronos Traffic",
    page_icon="🚦",
    layout="wide",
)

# Load Data
forecast = pd.read_csv("Data/Telemetry_Forecast.csv")

# Header + CSS
st.markdown("""
<div style='text-align:center;'>

<h1 style='font-size:58px;color:#e8cb2c;'>
🚦 CHRONOS TRAFFIC PROJECT
</h1>

<p style='font-size:24px;color:#a7bcd9;'>
AI-Driven Spatio-Temporal Traffic Forecasting
<br>
& Road Anomaly Detection System
</p>

<h4 style='text-align:center;color:#989b9c;margin-left:50px;'>
FINAL YEAR PROJECT PROTOTYPE
</h4>

</div>
""", unsafe_allow_html=True)

st.subheader("System Overview")

st.subheader("📂Dataset: Australian Traffic Telemetry")
st.markdown("""
<div style="font-size:20px;color:#989b9c;"
<p> • Prototype Telemetry Dataset • Trained on January–March Data • Used for Traffic Forecasting</p>
</div>
""", unsafe_allow_html=True)

st.divider()

# Metric Cards + CSS
st.markdown("""
<style>
.metric{
    background:#1F2937;
    padding:5px;
    border-radius:30px;
    height:100px;
    text-align:center;
    margin:auto;
}
</style>
""", unsafe_allow_html=True)

c1,c2,c3,c4 = st.columns(4)

with c1:
    st.markdown(f"""
    <div class="metric">
    <h4>📍 Locations</h4>
    <h1 style="color:#e8cb2c; margin:-30px; font-size:40px;">{forecast["location"].nunique()}</h1>
    </div>
""", unsafe_allow_html=True)

with c2:
    st.markdown(f"""
    <div class="metric">
    <h4>🧭 Directions</h4>
    <h1 style="color:#e8cb2c; margin:-30px; font-size:40px;">{forecast["heading"].nunique()}</h1>
    </div>
""", unsafe_allow_html=True)

with c3:
    st.markdown(f"""
    <div class="metric">
    <h4>📊 Records</h4>
    <h1 style="color:#e8cb2c; margin:-30px; font-size:40px;">{len(forecast):}</h1>
    </div>
""", unsafe_allow_html=True)

with c4:
    st.markdown(f"""
    <div class="metric">
    <h4>✨ AI Models</h4>
    <h1 style="color:#e8cb2c; margin:-30px; font-size:30px;"> &nbsp Prophet + CNN</h1>
    </div>
""", unsafe_allow_html=True)

# CSS for Feature boxes
st.markdown("""
<style>
.feature-card{
    background-color:#1F2937;
    border-radius:15px;
    padding:20px;
    border-left:5px solid #3B82F6;
    height:230px;
    width:auto;
    margin:auto;
}

.feature-card h3{
    color:white;
}

.feature-card p{
    color:#CBD5E1;
    font-size:16px;
    line-height:1.5;
}

.feature-card:hover{
    border-color:#60A5FA;
    box-shadow:0 0 18px rgba(59,130,246,.35);
}
</style>
""", unsafe_allow_html=True)

col1,col2,col3,col4=st.columns(4)

with col1:
    st.markdown("""
    <div class="feature-card">
    <h3>📈 Traffic Forecasting</h3>
    <p> Predict future traffic volumes using Facebook Prophet for intelligent congestion forecasting.</p>
    </div>
""", unsafe_allow_html=True)

with col2:
    st.markdown("""
    <div class="feature-card">
    <h3>📊 Historical Analysis</h3>
    <p> Analyze historical traffic trends with interactive charts and statistics.</p>
    </div>
""", unsafe_allow_html=True)

with col3:
    st.markdown("""
    <div class="feature-card">
    <h3>🚨 Anomaly Detection</h3>
    <p> Identify accidents and challenging road situations using a CNN-based image classifier.</p>
    </div>
""", unsafe_allow_html=True)

with col4:
    st.markdown("""
    <div class="feature-card">
    <h3>🗺️ Interactive Dashboard</h3>
    <p> Visualize traffic forecasts, congestion levels and anomaly alerts in one place.</p>
    </div>
""", unsafe_allow_html=True)

st.divider()

st.subheader("📖 About Chronos Traffic")
st.markdown("""
<div style="font-size:20px;color:#989b9c;"
<p>Chronos Traffic is an AI-powered Intelligent Transportation System prototype that combines traffic forecasting and road anomaly detection.

The system predicts future traffic congestion using Facebook Prophet and classifies road scenes into Normal Traffic, Accident, 
and Challenging Environment using a Convolutional Neural Network (CNN).</p>
</div>
""", unsafe_allow_html=True)

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