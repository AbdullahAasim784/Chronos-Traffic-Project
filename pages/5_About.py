import streamlit as st

# Page Settings
st.set_page_config(
    page_title="About",
    page_icon="ℹ️",
    layout="wide"
)

# Header + paragraph
st.title("ℹ️ About Chronos-Traffic")
st.markdown("""
<div style="font-size:20px;color:#989b9c;"
<p><b>Chronos-Traffic</b> is an AI-powered traffic forecasting prototype developed
    to analyze historical traffic patterns and predict future traffic volume
    using machine learning techniques.</p>
</div>
""", unsafe_allow_html=True)
st.divider()

# Overview
st.header("📌 Project Overview")
st.markdown("""
<div style="font-size:20px;color:#989b9c;"
<p>Chronos-Traffic provides an interactive dashboard for exploring historical
traffic data, evaluating forecasting performance, and generating future
traffic predictions. The system demonstrates how time-series forecasting
can support smarter traffic monitoring and decision-making.</p>
</div>
""", unsafe_allow_html=True)

st.divider()

# Project Information
st.header("🎓 Project Information ")

info_col1, info_col2 = st.columns(2)

with info_col1:
    st.markdown("""
    <style>
    .info-head{
        font-size:20px;
        color:white;
    }

    .info-desc{
        font-size:20px;
        color:#989b9c;
        margin-left:5px;
    }
    </style>

    <br>
    <ol>
        <div class="info-head"><b>Project Type:</b>
            <span class="info-desc">Final Year Project Prototype</span>
        </div> 
    </ol>
    
    <ol>
        <div class="info-head"><b>Institution:</b>
            <span class="info-desc">Bahria University Karachi Campus</span>
        </div> 
    </ol>

    <ol>
        <div class="info-head"><b>Department:</b>
            <span class="info-desc">Computer Science</span>
        </div>
    </ol>
 
    <ol>
        <div class="info-head"><b>Supervisor:</b>
            <span class="info-desc">Ms. Asia Samreen</span>
        </div> 
    </ol>

    """, unsafe_allow_html=True)

with info_col2:
    st.subheader("Project Team")
    st.markdown("""
    <div style="font-size:20px;color:#989b9c;">
    <li> Shaheer Ali Babar — 02-134231-088 </li>
    <li> Abdullah Aasim Kaker — 02-134231-004 </li>
    <li> Muhammad Ahmer — 02-235231-022 </li>
    </div>
    """, unsafe_allow_html=True)

st.divider()

# Objectives
st.header("🎯 Project Objectives")
st.markdown("""
<style>
.objective-card{
    background:#1F2937;
    border-left:5px solid #3B82F6;
    border-radius:12px;
    padding:18px;
    font-size:18px;
    color:#989b9c;
}
</style>
""", unsafe_allow_html=True)

col1, col2 = st.columns(2)

with col1:
    st.markdown("""
    <div class="objective-card">
    <li><b>Forecast future traffic volume</b></li>
    <li><b>Analyze historical traffic trends</b></li>
    <li><b>Visualize traffic patterns</b></li>
    </div>
    """, unsafe_allow_html=True)

with col2:
    st.markdown("""
    <div class="objective-card">
    <li><b>Evaluate forecasting accuracy</b></li>
    <li><b>Support traffic management</b></li>
    <li><b>Provide interactive dashboards</b></li>
    </div>
    """, unsafe_allow_html=True)

st.divider()

# Workflow
st.header("🔄 System Workflow")
# CSS
st.markdown("""
<style>
.workflow-card{
    background:#1F2937;
    color:#F8FAFC;
    padding:16px 20px;
    border-radius:14px;
    border-left:5px solid #3B82F6;
    font-weight:600;
    white-space:nowrap;
}

.workflow-arrow{
    font-size:30px;
    color:#60A5FA;
    font-weight:bold;
}

.workflow-container{
    display:flex;
    align-items:center;
    justify-content:center;
    flex-wrap:wrap;
    gap:16px;
    padding:20px;
}
</style>
""", unsafe_allow_html=True)
# Class
st.markdown("""
<div class="workflow-container">
<div class="workflow-card">📥 Data Collection</div>
<div class="workflow-arrow">➜</div>
<div class="workflow-card">🧹 Data Cleaning</div>
<div class="workflow-arrow">➜</div>
<div class="workflow-card">⚙️ Data Preprocessing</div>
<div class="workflow-arrow">➜</div>
<div class="workflow-card">✨ Prophet Model</div>
<div class="workflow-arrow">➜</div>
<div class="workflow-card">📈 Traffic Forecasting</div>
<div class="workflow-arrow">➜</div>
<div class="workflow-card">📊 Dashboard Visualization</div>
</div>
""", unsafe_allow_html=True)

st.divider()

# Features
st.header("System Features")
feature1, feature2 = st.columns(2)

with feature1:
    st.markdown("""
    <div style="font-size:20px;color:#989b9c;">
    <li> Historical Traffic Analysis </li>
    <li> Interactive Location Filtering </li>
    <li> Trend Visualization </li>
    <li> Model Validation</li>
    </div>
""", unsafe_allow_html=True)

with feature2:
    st.markdown("""
    <div style="font-size:20px;color:#989b9c;">
    <li> Future Traffic Forecasting </li>
    <li> Confidence Interval Graphs </li>
    <li> Performance Metrics </li>
    <li> Responsive Dashboard </li>
    </div>
""", unsafe_allow_html=True)

st.divider()

# Forecasting Model
st.header("Forecasting Model")
st.markdown("""
<div style="font-size:20px;color:#989b9c;"
<p> This prototype uses the <b>Facebook Prophet</b> time-series forecasting model.
The model learns historical traffic trends and seasonal patterns to predict
future vehicle counts.</p>
</div>
""", unsafe_allow_html=True)

model_col1, model_col2 = st.columns(2)

with model_col1:
    st.subheader("Input")
    st.markdown("""
    <div style="font-size:20px;color:#989b9c;">
    <li>Datetime</li>
    <li>Vehicle Count</li>
    </div>
""", unsafe_allow_html=True)

with model_col2:
    st.subheader("Output")
    st.markdown("""
    <div style="font-size:20px;color:#989b9c;">
    <li>Predicted Vehicle Count</li>
    <li>Confidence Interval</li>
    </div>
""", unsafe_allow_html=True)

st.divider()

# Dataset
st.header("📂 Dataset")
st.markdown("""
    <div style="font-size:20px;color:#989b9c;">
    <p> Prototype Dataset Information: </p>
    <li> Three months of telemetry data (Jan-Mar) </li>
    <li> 15-minute traffic observations </li>
    <li> Multiple monitoring locations </li>
    <li> Multiple travel directions </li>
    </div>
""", unsafe_allow_html=True)

st.divider()

# Technologies
st.header("🛠️ Technologies Used")
st.markdown("""
<style>
.tech-card{
    display:flex;
    flex-wrap:wrap;
    background:#1F2937;
    border:1px solid #334155;
    border-radius:20px;
    border-color:#60A5FA;
    border-width:2px;
    padding:22px;
    margin-bottom:18px;
    text-align:center;
    width:350px;
    height:100px;
}

.tech-icon{
    font-size:38px;
    margin-bottom:8px;
    padding-left:20px
}

.tech-title{
    color:#60A5FA;
    margin-top:13px;
    font-size:20px;
    font-weight:700;
}
</style>
""", unsafe_allow_html=True)

col1, col2, col3 = st.columns(3)

with col1:
    st.markdown("""
    <div class="tech-card">
        <div class="tech-icon">🐍</div> 
        <div class="tech-title">Python</div>
    </div>

    <div class="tech-card">
        <div class="tech-icon">📊</div>
        <div class="tech-title">Pandas</div>
    </div>
""", unsafe_allow_html=True)

with col2:
    st.markdown("""
    <div class="tech-card">
        <div class="tech-icon">📈</div>
        <div class="tech-title">Plotly</div>
    </div>

    <div class="tech-card">
        <div class="tech-icon">🌐</div>
        <div class="tech-title">Streamlit</div>
    </div>
    """, unsafe_allow_html=True)

with col3:
    st.markdown("""
    <div class="tech-card">
        <div class="tech-icon">✨</div>
        <div class="tech-title">Facebook Prophet</div>
    </div>

    <div class="tech-card">
        <div class="tech-icon">📉</div>
        <div class="tech-title">Time-Series Forecasting</div>
    </div>
    """, unsafe_allow_html=True)

st.divider()

# Performance Evaluation
st.header("📊 Model Evaluation")
st.markdown("""
    <div style="font-size:20px;color:#989b9c;">
    <p> The forecasting model is evaluated using: </p>
    <li> Mean Absolute Error (MAE) </li>
    <li> Root Mean Squared Error (RMSE) </li>
    <li> Mean Absolute Percentage Error (MAPE) </li>
    <p> These metrics measure how closely the predicted traffic volumes match the actual observed traffic data. </p>
    </div>
""", unsafe_allow_html=True)

st.divider()

# Future Enhancements
st.header("Future Enhancements")
st.markdown("""
    <div style="font-size:20px;color:#989b9c;">
    <li> Real-time traffic integration </li>
    <li> Live congestion prediction </li>
    <li> Interactive traffic heatmaps </li>
    <li> Deep Learning (LSTM/CNN) </li>
    <li> API integration </li>
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