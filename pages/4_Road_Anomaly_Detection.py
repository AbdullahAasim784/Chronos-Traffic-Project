import streamlit as st
import numpy as np
import pandas as pd
import tensorflow as tf
import plotly.express as px
from PIL import Image
import os

# Page Settings
st.set_page_config(
    page_title="Road Anomaly Detection",
    page_icon="🚨",
    layout="wide"
)

# Load Trained Model
def load_model():
    return tf.keras.models.load_model("Models/chronos_traffic_model.keras")
model = load_model()

# Class Names
CLASS_NAMES = {0: "✅ Normal Traffic",1: "🚨 Accident",2: "⚠️ Challenging Environment"}

# Prediction Function
def predict_image(img):
    img = img.resize((224,224))
    img_array = np.array(img)
    img_array = img_array / 255.0
    img_array = np.expand_dims(img_array, axis=0)
    prediction = model.predict(img_array, verbose=0)
    predicted_class = np.argmax(prediction)
    confidence = np.max(prediction) * 100
    return predicted_class, confidence, prediction[0]

# Header
st.markdown("""
    <h1 style="font-size:46px;font-weight:800;margin-bottom:0;">
    🚨 Road Anomaly Detection
    </h1>

    <p style="color:#989b9c;font-size:20px;margin-top:6px; margin-left:75px;"> 
    CNN-based Traffic Scene Classification for Smart Traffic Monitoring
    </p>
""", unsafe_allow_html=True)

st.divider()

# Image Selection
left, gap, right = st.columns([1,0.08,1.8])
uploaded_image = None

# Left: Image Source
with left:
    st.subheader("📂 Image Source")
    image_option = st.radio("",["Upload Image", "Sample Dataset"],horizontal=True)
    st.markdown("<br>", unsafe_allow_html=True)

    if image_option == "Upload Image":
        uploaded_image = st.file_uploader(
            "Upload Road Image",
            type=["jpg","jpeg","png"],
            label_visibility="collapsed"
        )
    else:
        dataset_path = "Data/processed_frames (India)/Final_videos"

        classes = sorted([
            f for f in os.listdir(dataset_path)
            if os.path.isdir(os.path.join(dataset_path,f))
        ])

        selected_class = st.selectbox("Class", classes)
        class_path = os.path.join(dataset_path, selected_class)

        videos = sorted([
            f for f in os.listdir(class_path)
            if os.path.isdir(os.path.join(class_path,f))
        ])

        selected_video = st.selectbox("Video Folder",videos)
        video_path = os.path.join(class_path, selected_video)

        images = sorted([
            f for f in os.listdir(video_path)
            if f.lower().endswith((".jpg",".jpeg",".png"))
        ])

        selected_image = st.selectbox("Frame",images)

        img_path = os.path.join(video_path, selected_image)

        uploaded_image = Image.open(img_path)

    st.markdown("<br>", unsafe_allow_html=True)

    c1,c2,c3 = st.columns([1,2,1])
    with c2:
        predict = st.button("🔍 Analyze Image",use_container_width=True)

# Right: Image Preview
with right:
    st.subheader("🖼️ Image Preview")
    preview = st.container(border=True)

    with preview:
        if uploaded_image is not None:
            if image_option == "Upload Image":
                display_img = Image.open(uploaded_image)
            else:
                display_img = uploaded_image
            st.image(display_img,width=600)

        else:
            st.markdown("<br><br>", unsafe_allow_html=True)
            st.markdown("""
                <h2 style="text-align:center;color:#94A3B8;">📷</h2>
                <h4 style="text-align:center;color:#94A3B8;">No Image Selected</h4>

                <p style="text-align:center;color:#64748B;font-size:16px;">
                Upload an image or choose one from the sample dataset.
                </p>
            """,unsafe_allow_html=True)

# Prediction Section
if predict:
    if uploaded_image is None:
        st.warning("⚠️ Please upload or select an image first.")
    else:
        if image_option == "Upload Image":
            img = Image.open(uploaded_image)
        else:
            img = uploaded_image

        # Predict
        predicted_class, confidence, probabilities = predict_image(img)

        if predicted_class == 0:
            impact = "🟢 LOW"
            action = "No immediate action required."
            border_color = "#22C55E"
            title_color = "#BBF7D0"
            value_color = "#4ADE80"
            bg_color = "#163323"

        elif predicted_class == 1:
            impact = "🔴 HIGH"
            action = "Emergency response recommended."
            border_color = "#EF4444"
            title_color = "#FECACA"
            value_color = "#F87171"
            bg_color = "#3A1A1A"

        else:
            impact = "🟠 MEDIUM"
            action = "Monitor traffic and alert authorities."
            border_color = "#F59E0B"
            title_color = "#FDE68A"
            value_color = "#FBBF24"
            bg_color = "#563F1F"

        left, divider, right = st.columns([1,0.03,1])

        with left:
            st.subheader("AI Prediction")
            st.markdown(f"""
                <div style="
                background:{bg_color};
                border:2px solid {border_color};
                border-radius:18px;
                padding:25px;">
                    <div class="pred-value" style="color:{value_color};margin-bottom:22px; font-size:22px;">
                        <b>{CLASS_NAMES[predicted_class]}</b>
                    </div>
                    <div class="pred-title" style="margin-top:20px;">
                        Confidence 
                    </div>
                    <div class="pred-value" style="color:{value_color};margin-bottom:22px;">
                        <b>{confidence:.2f}%</b>
                    </div>
                    <div class="pred-title" style="margin-top:20px;">
                        Traffic Impact
                    </div>
                    <div class="pred-value" style="color:{value_color};margin-bottom:22px;">
                        <b>{impact}</b>
                    </div>
                    <div class="pred-title" style="margin-top:20px;">
                        Recommended Action 
                    </div>
                    <div style="color:{value_color};font-size:18px;line-height:1.7;margin-top:10px;"> 
                        <b>{action}</b>
                    </div>
                </div>
            """, unsafe_allow_html=True)
            
        with divider:
            st.markdown("""
            <div style="
                border-left:2px solid #334155;
                height:435px;
                margin:auto;">
            </div>
            """, unsafe_allow_html=True)

        with right:
            st.subheader("📊 Confidence Scores")

            chart = pd.DataFrame({
                "Class": ["Normal Traffic","Accident","Challenging"],
                "Confidence": [probabilities[0] * 100, probabilities[1] * 100, probabilities[2] * 100]
            })

            fig = px.bar(
                chart,
                x="Confidence",
                y="Class",
                orientation="h",
                text="Confidence",
                color="Confidence",
                color_continuous_scale="Blues"
            )

            fig.update_traces(texttemplate="%{text:.1f}%", textposition="outside")

            fig.update_layout(
                height=360,
                plot_bgcolor="#111827",
                paper_bgcolor="#1F2937",
                coloraxis_showscale=False,
                margin=dict(l=20,r=20,t=20,b=20),
                xaxis_title="Confidence (%)",
                yaxis_title="",
                xaxis_range=[0,100]
            )

            st.plotly_chart(fig, use_container_width=True)

st.divider()

# Model Information
st.subheader("📋 Model Information")

# Model Info Card CSS
st.markdown("""
<style>
.anomaly-card{
    display:flex;
    justify-content:space-evenly;
    align-items:center;
    background:#1F2937;
    border:1px solid #334155;
    border-radius:20px;
    padding:20px;
}

.anomaly-card:hover{
    border-color:#3B82F6;
    box-shadow:0 0 15px rgba(59,130,246,0.25);
}

.anomaly-item{
    flex:1;
    text-align:center;
}

.anomaly-title{
    font-size:22px;
    font-weight:700;
    color:#F8FAFC;
    margin-bottom:10px;
}

.anomaly-value{
    font-size:28px;
    font-weight:700;
    color:#FACC15;
}

.anomaly-divider{
    width:2px;
    height:70px;
    background:#475569;
}
</style>
""", unsafe_allow_html=True)

# Model Info Card Class
st.markdown("""
<div class="anomaly-card">
    <div class="anomaly-item">
        <div class="anomaly-title">Model</div>
        <div class="anomaly-value">CNN</div>
    </div>
    <div class="anomaly-divider"></div>
    <div class="anomaly-item">
        <div class="anomaly-title">Classes</div>
        <div class="anomaly-value">3</div>
    </div>
    <div class="anomaly-divider"></div>
    <div class="anomaly-item">
        <div class="anomaly-title">Validation Accuracy</div>
        <div class="anomaly-value">67%</div>
    </div>
    <div class="anomaly-divider"></div>
    <div class="anomaly-item">
        <div class="anomaly-title">Status</div>
        <div class="anomaly-value">Prototype</div>
    </div>
</div>
""", unsafe_allow_html=True)

st.divider()

# Dataset Information
st.subheader("📂 Dataset Summary")
c1, c2 = st.columns(2)

# Dataset Classes
with c1:
    st.markdown("""
        <div style="font-size:20px;color:#989b9c;">
        <h3 style="color:white;"> Dataset Classes: </h3>
        <li> ✅ Normal Traffic </li>
        <li> 🚨 Accident </li>
        <li> ⚠ Challenging Environment</li>
        <p style="font-size:18px;">The CNN was trained using labeled traffic scene images extracted from videos.</p>
        </div>
    """, unsafe_allow_html=True)

# Classification Goal
with c2:
    st.markdown("""
        <div style="font-size:20px;color:#989b9c;">
        <h3 style="color:white;"> Classification Goal: </h3>
        <li> Normal Traffic </li>
        <li> Accident </li>
        <li> Challenging Environment</li>
        <p style="font-size:18px;">This module demonstrates AI-assisted road anomaly detection within the Chronos-Traffic prototype.</p>
        </div>
    """, unsafe_allow_html=True)

st.divider()

# Notes
st.subheader("📝 Model Notes")

# CSS
st.markdown("""
<style>
.notes-card{
    background:#1F2937;
    border:1px solid #334155;
    border-radius:18px;
    padding:28px;
    transition:0.3s;
}

.notes-card:hover{
    border-color:#3B82F6;
    box-shadow:0 0 15px rgba(59,130,246,0.25);
}

.notes-title{
    font-size:28px;
    font-weight:700;
    color:#F8FAFC;
    margin-bottom:18px;
}

.notes-text{
    color:#CBD5E1;
    font-size:17px;
    line-height:1.8;
}

.notes-subtitle{
    color:#FACC15;
    font-size:22px;
    font-weight:700;
    margin-top:22px;
    margin-bottom:12px;
}

.notes-list{
    color:#E2E8F0;
    font-size:17px;
    line-height:2;
}

</style>
""", unsafe_allow_html=True)

# Notes Card
st.markdown("""
<div class="notes-card">

<div class="notes-title">
Model Overview
</div>

<div class="notes-text">
This anomaly detection module is a proof-of-concept developed using an available labelled traffic dataset.
The objective is to demonstrate the integration of AI-based road scene classification within the
Chronos-Traffic Intelligent Transportation System dashboard.

The current CNN model classifies road scenes into three categories:
<b>Normal Traffic</b>, <b>Accident</b>, and <b>Challenging Environment</b>.
Although designed as a prototype, it demonstrates the feasibility of integrating computer vision
into real-time traffic monitoring.
</div>

<div class="notes-subtitle">
🚀 Future Improvements
</div>

<div class="notes-list">
• Larger and more diverse traffic datasets<br>
• CNN + LSTM / Vision Transformer architectures<br>
• Real-time CCTV and roadside camera integration<br>
• Detection of flooding, road blockages, potholes, and construction zones<br>
</div>

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
