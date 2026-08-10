import streamlit as st
import pandas as pd
import plotly.express as px

# Page Settings
st.set_page_config(
    page_title="Model Performance",
    page_icon="Assets/Model_icon.png",
    layout="wide"
)

# Load Data
validation = pd.read_csv("Data/Model_Validation.csv")
performance = pd.read_csv("Data/Model_Performance.csv")
validation["datetime"] = pd.to_datetime(validation["datetime"])

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
    locations = sorted(validation["location"].unique())
    location = st.selectbox("Select Location:", locations)

    headings = sorted(validation[validation["location"] == location]["heading"].unique())
    heading = st.selectbox("Select Direction:", headings)

validation_data = validation[
    (validation["location"] == location) &
    (validation["heading"] == heading)
].copy()

performance_data = performance[
    (performance["location"] == location) &
    (performance["heading"] == heading)
].copy()

with header_left:
    logo_col, title_col = st.columns([0.5, 5])

    with logo_col:
        st.markdown("<br>", unsafe_allow_html=True)
        st.image("Assets/Model_icon.png")

    with title_col:
        st.markdown("""
        <h1 style="font-size:46px;font-weight:800;margin-bottom:0;">
        Model Performance
        </h1>

        <p style="color:#989b9c;font-size:20px;margin-top:6px;">
        Evaluation of Prophet forecasting model using historical traffic data.
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

# Records Card CSS
st.markdown("""
<style>
.pred-card{
    background:#1F2937;
    border:1px solid #334155;
    border-radius:20px;
    padding:24px;
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
    height:70px;
    background:#475569;
}
</style>
""", unsafe_allow_html=True)

# Train/Test Results & Error Metrics
row = performance_data.iloc[0]
left, divider, right = st.columns([1, 0.03, 1])

with left:
    st.markdown(f"""
    <div class="pred-card">
        <h2>📚 Training & Validation</h2>
        <hr style="border:1px solid #334155;margin:10px ;">
        <div style="display:flex;justify-content:space-evenly;align-items:center;">
            <div class="pred-item">
                <div class="pred-title">Training Records</div>
                <div class="pred-value">{int(row["train_records"]):,}</div>
            </div>
            <div class="pred-divider"></div>
            <div class="pred-item">
                <div class="pred-title">Testing Records</div>
                <div class="pred-value">{int(row["test_records"]):,}</div>
            </div>
        </div>
        <div style="text-align:center;color:#94A3B8;font-size:14px;line-height:1.2;">
            The model was trained using an <b>80%</b> training split and validated using the remaining <b>20%</b>.
        </div>
    </div>
""", unsafe_allow_html=True)

with divider:
    st.markdown("""
    <div style="
        border-left:2px solid #CBD5E1;
        height:280px;
        margin:auto;">
    </div>
""", unsafe_allow_html=True)

with right:
    st.markdown(f"""
    <div class="pred-card">
        <h2>📈 Model Performance</h2>
        <hr style="border:1px solid #334155;margin:10px ;">
        <div style="display:flex;justify-content:space-evenly;align-items:center;">
            <div class="pred-item">
                <div class="pred-title">MAE</div>
                <div class="pred-value">{row["MAE"]:.2f}</div>
            </div>
            <div class="pred-divider"></div>
            <div class="pred-item">
                <div class="pred-title">RMSE</div>
                <div class="pred-value">{row["RMSE"]:.2f}</div>
            </div>
            <div class="pred-divider"></div>
            <div class="pred-item">
                <div class="pred-title">R² Score</div>
                <div class="pred-value">{row["R2"]:.3f}</div>
            </div>
        </div>
    </div>
 """, unsafe_allow_html=True)

st.divider()

# Actual vs Predicted Graph
st.subheader("Actual vs Predicted Traffic Counts")
st.markdown("""
<div style="font-size:16px;color:#989b9c;"
<p>Comparison of observed traffic counts with Prophet predictions and their confidence interval.</p>
</div>
""", unsafe_allow_html=True)

fig = px.line()

# Actual Values
fig.add_scatter(
    x=validation_data["datetime"],
    y=validation_data["actual"],
    mode="lines",
    name="Actual",
    line=dict(color="#60A5FA",width=3)
)

# Predicted Values
fig.add_scatter(
    x=validation_data["datetime"],
    y=validation_data["predicted"],
    mode="lines",
    name="Predicted",
    line=dict(color="#F97316",width=3)
)

# Upper Confidence Bound
fig.add_scatter(
    x=validation_data["datetime"],
    y=validation_data["max_predicted"],
    mode="lines",
    line=dict(width=0),
    showlegend=False,
)

# Lower Confidence Bound + Fill
fig.add_scatter(
    x=validation_data["datetime"],
    y=validation_data["min_predicted"],
    mode="lines",
    fill="tonexty",
    fillcolor="rgba(249,115,22,0.20)",
    line=dict(width=0),
    name="Confidence Interval",
)

fig.update_layout(
    height=450,
    plot_bgcolor="#111827",
    paper_bgcolor="#111827",
    hovermode="x unified",
    margin=dict(l=20,r=20,t=20,b=20),
    xaxis_title="Date & Time",
    yaxis_title="Vehicle Count",
    legend=dict(bgcolor="#202C47",bordercolor="#36518D",borderwidth=1)
)

st.plotly_chart(fig, use_container_width=True)

# Validation Results
st.subheader("Validation Results")
st.markdown("""
<div style="font-size:16px;color:#989b9c;"
<p>Select a validation date to inspect the actual and predicted traffic counts for each 15-minute interval.</p>
</div>
""", unsafe_allow_html=True)

# Create Date Column
validation_data["date"] = validation_data["datetime"].dt.date

# Available Dates
available_dates = sorted(validation_data["date"].unique())
selected_date = st.selectbox("Validation Date", available_dates)

# Filter Selected Date
day_data = validation_data[validation_data["date"] == selected_date].copy()
day_data["Time"] = day_data["datetime"].dt.strftime("%H:%M")

table = day_data[
    [
        "Time",
        "actual",
        "predicted",
        "max_predicted",
        "min_predicted",
        "error"
    ]
].rename(
    columns={
        "actual": "Actual Count",
        "predicted": "Predicted Count",
        "min_predicted": "Lower Bound",
        "max_predicted": "Upper Bound",
        "error": "Prediction Error"
    }
)

# Display Table
st.dataframe(table, use_container_width=True, hide_index=True)

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