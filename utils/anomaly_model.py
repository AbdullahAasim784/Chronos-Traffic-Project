"""Road anomaly CNN: loading the model, classifying an image or a video, and how each class is shown.

Used by pages/4_Road_Anomaly_Detection.py. TensorFlow and OpenCV are imported inside the
functions, so the page opens fast and they only load when Analyze is pressed.
"""
import json
import re
from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st

from utils.config import AMBER, GREEN, GREY, MODELS_DIR, RED, SKY

MODEL_PATH = MODELS_DIR / "traffic_anomaly_detection.keras"
CLASS_NAMES_PATH = MODELS_DIR / "class_names.json"   # same order the model was trained with
IMAGE_TYPES = (".jpg", ".jpeg", ".png", ".webp", ".bmp")
VIDEO_TYPES = (".mp4", ".mov", ".avi", ".mkv", ".webm", ".m4v")

# Same settings as the Colab test notebooks.
IMG_SIZE = (224, 224)
CONFIDENCE_THRESHOLD = 0.60    # below this -> "uncertain"
SAMPLE_FPS = 4                 # video: frames analysed per second
SMOOTH_SEC = 1.0               # video: rolling average window
SUSTAINED_SHARE = 0.20         # video: an anomaly must cover 20% of frames to be the verdict

# From Models/evaluation_report.txt (update these if you retrain).
MODEL_METRICS = {
    "test_images": 864,
    "correct": 831,
    "accuracy": 96.06,
    "macro_f1": 96.27,
    "per_class": {   # class name: (precision %, recall %)
        "accident": (99.7, 92.4),
        "flooded": (96.8, 98.9),
        "normal": (90.5, 100.0),
    },
}

# How each class name from class_names.json is shown. Unknown names get a neutral style.
CLASS_STYLE = {
    "normal": {"title": "Normal Traffic", "icon": "✅", "kind": "low", "impact": "Low",
               "action": "No immediate action required.", "color": GREEN},
    "accident": {"title": "Accident", "icon": "🚨", "kind": "high", "impact": "High",
                 "action": "Emergency response recommended.", "color": RED},
    "flooded": {"title": "Flooded Road", "icon": "🌊", "kind": "flood", "impact": "High",
                "action": "Divert traffic and alert the authorities.", "color": SKY},
    "uncertain": {"title": "Uncertain", "icon": "❔", "kind": "na", "impact": "Unknown",
                  "action": "Confidence is below 60%. Check the footage manually.", "color": GREY},
    "none": {"title": "No Sustained Anomaly", "icon": "✅", "kind": "low", "impact": "Low",
             "action": "No anomaly lasted long enough to raise an alert.", "color": GREEN},
}


def style(name):
    return CLASS_STYLE.get(str(name).lower(), {
        "title": str(name).replace("_", " ").title(), "icon": "⚠️", "kind": "medium", "impact": "Medium",
        "action": "Monitor traffic and alert authorities.", "color": AMBER})


# =================================================================
# Helpers
# =================================================================
@st.cache_resource(show_spinner=False)
def load_model():
    import tensorflow as tf  # imported here, so the page opens fast and TF loads only on Analyze
    return tf.keras.models.load_model(MODEL_PATH)


@st.cache_data(show_spinner=False)
def class_names():
    return json.loads(CLASS_NAMES_PATH.read_text(encoding="utf-8"))


def predict_image(path):
    """Same as training: RGB, 224x224, raw 0-255 values. The model's own Rescaling layer maps them to [-1, 1]."""
    import tensorflow as tf
    # bilinear resize = same as image_dataset_from_directory used in training
    img = tf.keras.utils.load_img(path, target_size=IMG_SIZE, interpolation="bilinear")  # RGB (drops PNG alpha)
    arr = tf.keras.utils.img_to_array(img)[None, ...]                 # NO /255 here
    probs = load_model().predict(arr, verbose=0)[0]
    names = class_names()
    top = int(probs.argmax())
    return {
        "kind": "image",
        "label": names[top] if probs[top] >= CONFIDENCE_THRESHOLD else "uncertain",
        "top": names[top],
        "confidence": float(probs[top]) * 100,
        "probs": {n: float(p) * 100 for n, p in zip(names, probs)},
    }


@st.cache_data(show_spinner=False, max_entries=10)
def analyse_video(path, modified):  # "modified" makes the cache refresh if the file changes
    """Like the Colab video test: 4 frames/s, BGR->RGB, 224x224, raw 0-255,
    1-second rolling average, 60% threshold, an anomaly verdict needs 20% of frames.
    Returns the same fields as predict_image, so both show the same result card."""
    import cv2

    names = class_names()
    cap = cv2.VideoCapture(path)
    if not cap.isOpened():
        raise ValueError("Could not open this video.")
    fps = cap.get(cv2.CAP_PROP_FPS) or 30
    step = max(1, round(fps / SAMPLE_FPS))
    batch, idx = [], 0
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        if idx % step == 0:
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)                     # OpenCV reads BGR; model wants RGB
            batch.append(cv2.resize(rgb, IMG_SIZE).astype("float32"))         # NO /255 here
        idx += 1
    cap.release()
    if not batch:
        raise ValueError("No frames could be read from this video.")

    probs = load_model().predict(np.stack(batch), batch_size=32, verbose=0)
    window = max(1, int(SMOOTH_SEC * SAMPLE_FPS))
    smooth = pd.DataFrame(probs, columns=names).rolling(window, min_periods=1, center=True).mean()
    top, conf = smooth.values.argmax(axis=1), smooth.values.max(axis=1)
    labels = [names[t] if c >= CONFIDENCE_THRESHOLD else "uncertain" for t, c in zip(top, conf)]

    labels = np.array(labels)

    # Verdict: an anomaly that covers 20% of frames wins; otherwise normal (or uncertain).
    anomalies = [n for n in names if n.lower() != "normal"]
    main = max(anomalies, key=lambda c: (labels == c).sum()) if anomalies else None
    if main and (labels == main).mean() >= SUSTAINED_SHARE:
        verdict = main
    elif "normal" in names and (labels == "normal").any():
        verdict = "normal"
    else:
        verdict = "uncertain"

    # Confidence = average probabilities over the frames that gave the verdict
    # (all frames if uncertain), so the card and the chart match, just like for images.
    segment = labels == verdict if verdict != "uncertain" else np.ones(len(labels), bool)
    avg = smooth[segment].mean()
    top = str(avg.idxmax())
    return {
        "kind": "video",
        "label": verdict,
        "top": top,
        "confidence": float(avg[verdict if verdict != "uncertain" else top]) * 100,
        "probs": {n: float(avg[n]) * 100 for n in names},
    }


def camera_info(path):
    """'Camera/camera001_KarsazRd/frame.jpg' -> (1, 'Karsaz Rd'). (None, None) if not from a camera folder."""
    for folder in Path(path).parents:
        match = re.match(r"camera0*(\d+)_(.+)", folder.name, re.IGNORECASE)
        if match:
            name = re.sub(r"(?<=[a-z])(?=[A-Z])", " ", match.group(2)).replace("_", " ")
            return int(match.group(1)), name
    return None, None


def media_kind(path):
    suffix = Path(path).suffix.lower()
    return "video" if suffix in VIDEO_TYPES else "image" if suffix in IMAGE_TYPES else None
