"""Road Anomaly Detection (admin): pick a camera image or video and classify it with the CNN."""
import base64
import sqlite3
import tempfile
from html import escape
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from utils.admin_ui import admin_header, setup_admin_page
from utils.anomaly_model import (
    CLASS_NAMES_PATH, CONFIDENCE_THRESHOLD, IMAGE_TYPES, MODEL_METRICS, MODEL_PATH, SAMPLE_FPS,
    SUSTAINED_SHARE, VIDEO_TYPES, analyse_video, camera_info, media_kind, predict_image, style,
)
from utils.anomaly_store import alerts_on_day, camera_list, resolve_user_id, save_detection
from utils.config import CAMERA_DIR, CHART_TEXT, GOLD, ROOT, SURFACE, now_karachi
from utils.ui import divider, footer

# Admin page: same setup, login check and sidebar as the other admin pages.
PAGE_TITLE = "Road Anomaly Detection"
setup_admin_page(PAGE_TITLE, "🚨", "anomaly.css")

# Arriving from another page: start empty (no old image, result or error).
if st.session_state.get("ct_previous_page") != PAGE_TITLE:
    for _key in ("anomaly_file", "anomaly_result", "anomaly_error", "anomaly_upload_name"):
        st.session_state.pop(_key, None)

def pick_file():
    """Native Windows file dialog that opens straight in the Camera folder.
    Works when Streamlit runs on this PC (your demo). Raises if there is no desktop."""
    import tkinter as tk
    from tkinter import filedialog

    root = tk.Tk()
    root.withdraw()
    root.wm_attributes("-topmost", 1)   # dialog appears in front of the browser
    try:
        path = filedialog.askopenfilename(
            parent=root,
            title="Choose a camera image or video",
            initialdir=str(CAMERA_DIR if CAMERA_DIR.is_dir() else ROOT),
            filetypes=[
                ("Images and videos", " ".join("*" + t for t in IMAGE_TYPES + VIDEO_TYPES)),
                ("Images", " ".join("*" + t for t in IMAGE_TYPES)),
                ("Videos", " ".join("*" + t for t in VIDEO_TYPES)),
            ],
        )
    finally:
        root.destroy()
    return path or None


def set_file(path):
    st.session_state["anomaly_file"] = path
    st.session_state.pop("anomaly_result", None)
    st.session_state.pop("anomaly_error", None)


def clear_file():
    """Red X button: forget the selected file and its result."""
    for key in ("anomaly_file", "anomaly_result", "anomaly_error", "anomaly_upload_name"):
        st.session_state.pop(key, None)
    # A new key gives the fallback upload box a fresh, empty state.
    st.session_state["anomaly_upload_n"] = st.session_state.get("anomaly_upload_n", 0) + 1


def choose_file():
    """Choose button callback: runs before the page redraws, so the preview updates at once."""
    try:
        path = pick_file()
    except Exception:  # no desktop available (e.g. deployed online) -> show an upload box instead
        st.session_state["picker_unavailable"] = True
        return
    if path:
        set_file(path)


def image_tag(path):
    mime = "png" if Path(path).suffix.lower() == ".png" else "jpeg"
    data = base64.b64encode(Path(path).read_bytes()).decode()
    return f'<img class="ct-preview-img" src="data:image/{mime};base64,{data}" alt="Selected frame">'


def camera_text(cam_id, cam_name):
    return f"CAM {cam_id:03d} · {cam_name}" if cam_id is not None else "Uploaded file"


# =================================================================
# Header: same gold header, Log Out and date/time pill as the other admin pages
# =================================================================
admin_header("Road Anomaly Detection", "Classify camera footage for accidents and other road anomalies")


# =================================================================
# Workspace: preview (70%) on the left, controls (30%) on the right.
# The right column is filled first so the preview already shows a newly uploaded file.
# =================================================================
with st.container(key="anomaly_workspace"):
    st.markdown(
        '<div class="ct-ws-head"><span class="ct-ws-kicker">◉ &nbsp; ANALYZE CAMERA FOOTAGE</span>'
        '<span class="ct-ws-hint">4 Karachi road cameras</span></div>',
        unsafe_allow_html=True,
    )
    preview_col, controls_col = st.columns([7, 3], gap="large", vertical_alignment="top")

    with controls_col, st.container(key="anomaly_controls"):
        st.button(
            "📂  Choose Image / Video", key="anomaly_choose", use_container_width=True,
            on_click=choose_file, help="Opens the Camera folder",
        )

        # Fallback when no desktop dialog is available: a normal upload box.
        if st.session_state.get("picker_unavailable"):
            uploaded = st.file_uploader(
                "Upload a camera image or video", type=[t.strip(".") for t in IMAGE_TYPES + VIDEO_TYPES],
                key=f"anomaly_upload_{st.session_state.get('anomaly_upload_n', 0)}",
            )
            if uploaded is not None and st.session_state.get("anomaly_upload_name") != uploaded.name:
                temp_path = Path(tempfile.gettempdir()) / f"chronos_{uploaded.name}"
                temp_path.write_bytes(uploaded.getvalue())
                st.session_state["anomaly_upload_name"] = uploaded.name
                set_file(str(temp_path))

        file_path = st.session_state.get("anomaly_file")
        if file_path and not Path(file_path).is_file():   # moved or deleted since it was chosen
            file_path = None
            st.session_state.pop("anomaly_file", None)

        if file_path:
            cam_id, cam_name = camera_info(file_path)
            kind = media_kind(file_path)
            st.markdown(
                '<div class="ct-src-card">'
                f'<div class="ct-src-badge">{"CAM " + format(cam_id, "03d") if cam_id is not None else "FILE"}</div>'
                f'<div class="ct-src-place">{escape(cam_name or "Uploaded file")}</div>'
                '<div class="ct-src-rows">'
                f'<div><span>File</span><strong title="{escape(Path(file_path).name)}">{escape(Path(file_path).name)}</strong></div>'
                f'<div><span>Type</span><strong>{"Video" if kind == "video" else "Image"}</strong></div>'
                "</div></div>",
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                '<div class="ct-src-card ct-src-empty">'
                '<div class="ct-src-place">No file selected</div>'
                '<div class="ct-src-note">Choose a frame or clip from one of the camera folders.</div>'
                "</div>",
                unsafe_allow_html=True,
            )

        analyze = st.button(
            "🔍  Analyze", key="anomaly_analyze", type="primary",
            use_container_width=True, disabled=not file_path,
        )

        model_ready = MODEL_PATH.is_file() and CLASS_NAMES_PATH.is_file()
        st.markdown(
            f'<div class="ct-model-chip {"ready" if model_ready else "missing"}"><span></span>'
            f'{"CNN model ready" if model_ready else "Model or class_names.json missing"}</div>',
            unsafe_allow_html=True,
        )

        if analyze and file_path:
            st.session_state.pop("anomaly_error", None)
            st.session_state.pop("anomaly_result", None)
            if not model_ready:
                st.session_state["anomaly_error"] = (
                    f"Put {MODEL_PATH.name} and {CLASS_NAMES_PATH.name} in the Models folder.")
            else:
                is_video = media_kind(file_path) == "video"
                try:
                    with st.spinner("Analyzing video frames…" if is_video else "Analyzing image…"):
                        result = (analyse_video(file_path, Path(file_path).stat().st_mtime) if is_video
                                  else predict_image(file_path))
                except ImportError:
                    st.session_state["anomaly_error"] = "Video analysis needs OpenCV. Run: pip install opencv-python"
                except Exception as exc:  # unreadable file, model/class mismatch, ...
                    st.session_state["anomaly_error"] = f"Analysis failed: {exc}"
                else:
                    cam_id, cam_name = camera_info(file_path)
                    result.update(file=Path(file_path).name, camera=camera_text(cam_id, cam_name),
                                  time=now_karachi().strftime("%d %b · %I:%M %p"))
                    # Store accident / flooded / uncertain results in anomaly_logs (Karachi time).
                    try:
                        result["log"] = save_detection(
                            cam_id, result["label"], result["confidence"],
                            resolve_user_id(st.session_state.get("user")),
                        )
                    except sqlite3.Error as exc:
                        result["log"] = ("error", str(exc))
                    st.session_state["anomaly_result"] = result

    with preview_col:
        with st.container(key="anomaly_preview"):
            if file_path:
                st.button("✕", key="anomaly_clear", help="Remove this file", on_click=clear_file)
            if not file_path:
                folder_note = ("Opens the <strong>Camera</strong> folder with all four road cameras."
                               if CAMERA_DIR.is_dir() else
                               "Create a <strong>Camera</strong> folder in the project with the four camera folders.")
                st.markdown(
                    '<div class="ct-preview-empty">'
                    '<div class="ct-preview-icon">📷</div>'
                    '<div class="ct-preview-title">No image or video selected</div>'
                    f'<div class="ct-preview-text">Click <strong>Choose Image / Video</strong>. {folder_note}</div>'
                    "</div>",
                    unsafe_allow_html=True,
                )
            elif media_kind(file_path) == "video":
                st.video(file_path)
            else:
                cam_id, cam_name = camera_info(file_path)
                st.markdown(
                    '<div class="ct-preview-wrap">' + image_tag(file_path) +
                    f'<span class="ct-preview-chip">● {escape(camera_text(cam_id, cam_name))}</span></div>',
                    unsafe_allow_html=True,
                )

if st.session_state.get("anomaly_error"):
    st.warning(st.session_state["anomaly_error"])


# =================================================================
# Results: class label, confidence and chart
# =================================================================
def probability_layout(fig, height, title):
    fig.update_layout(
        title=dict(text=title, font=dict(size=14, color="#cfdcec"), x=0),
        height=height, margin=dict(l=10, r=40, t=40, b=10),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(255,255,255,0.025)",
        font=dict(color=CHART_TEXT), hoverlabel=dict(bgcolor=SURFACE, bordercolor=GOLD),
    )
    return fig


def bar_chart(values, highlight, title):
    """Horizontal % bars per class, the highlighted one solid, with the 60% threshold line."""
    names = list(values)
    fig = go.Figure(go.Bar(
        x=[values[n] for n in names], y=[style(n)["title"] for n in names], orientation="h",
        marker=dict(color=[style(n)["color"] for n in names],
                    opacity=[1 if n == highlight else 0.45 for n in names], line=dict(width=0)),
        text=[f"{values[n]:.1f}%" for n in names], textposition="outside",
        textfont=dict(color="#e6f1ff", size=13),
        hovertemplate="%{y}: <b>%{x:.1f}%</b><extra></extra>",
    ))
    fig.add_vline(x=CONFIDENCE_THRESHOLD * 100, line=dict(color="rgba(148,163,184,.6)", dash="dash", width=1))
    probability_layout(fig, 300, title).update_layout(
        bargap=0.45, showlegend=False,
        xaxis=dict(range=[0, 112], ticksuffix="%", tickvals=[0, 25, 50, 75, 100],
                   gridcolor="rgba(148,163,184,.12)", fixedrange=True),
        yaxis=dict(autorange="reversed", fixedrange=True),
    )
    return fig


def log_note(log):
    """Small line under the result: was it saved to the alerts log?"""
    outcome, detail = log or (None, None)
    if outcome == "saved":
        return '<div class="ct-log-note saved">✓ Saved to today\'s anomaly alerts</div>'
    if outcome == "duplicate":
        when = pd.to_datetime(detail, errors="coerce")
        when = when.strftime("%I:%M %p").lstrip("0") if pd.notna(when) else detail
        return (f'<div class="ct-log-note">Already logged for this camera at {escape(str(when))} '
                "· not saved again</div>")
    if outcome == "not_logged":
        return '<div class="ct-log-note">Normal traffic · not added to alerts</div>'
    if outcome == "no_camera":
        return '<div class="ct-log-note warn">Not saved · the file is not from a registered camera folder</div>'
    if outcome == "error":
        return f'<div class="ct-log-note warn">Could not save: {escape(str(detail))}</div>'
    return ""


def verdict_card(info, big, big_note, cells, bar=None):
    grid = "".join(f"<div><span>{k}</span><strong>{escape(str(v))}</strong></div>" for k, v in cells)
    track = f'<div class="ct-conf-track"><span style="width:{bar:.1f}%"></span></div>' if bar is not None else ""
    return (
        f'<div class="ct-verdict ct-verdict-{info["kind"]}">'
        '<div class="ct-verdict-kicker">PREDICTED CLASS</div>'
        f'<div class="ct-verdict-label">{info["icon"]} {info["title"]}</div>'
        f'<div class="ct-verdict-conf"><span>{big}</span> {big_note}</div>{track}'
        f'<div class="ct-verdict-grid">{grid}</div>'
        f'<div class="ct-verdict-action"><span>Recommended action</span>{info["action"]}</div>'
        "</div>"
    )


result = st.session_state.get("anomaly_result")
if result:
    info = style(result["label"])
    divider()
    with st.container(key="anomaly_result_panel"):
        st.markdown(
            '<div class="ct-ws-head"><span class="ct-ws-kicker">◉ &nbsp; ANALYSIS RESULT</span>'
            f'<span class="ct-ws-hint">{escape(result["file"])}</span></div>',
            unsafe_allow_html=True,
        )
        verdict_col, chart_col = st.columns([1, 1.25], gap="large", vertical_alignment="center")

        cells = [("Traffic impact", info["impact"]), ("Camera", result["camera"]), ("Analyzed", result["time"])]
        if result["label"] == "uncertain":
            cells[0] = ("Top guess", f'{style(result["top"])["title"]} {result["confidence"]:.0f}%')
        with verdict_col:
            st.markdown(verdict_card(info, f'{result["confidence"]:.1f}%', "confidence", cells,
                                     bar=result["confidence"]) + log_note(result.get("log")),
                        unsafe_allow_html=True)
        with chart_col, st.container(key="anomaly_chart_card"):
            st.plotly_chart(bar_chart(result["probs"], result["top"], "Confidence by class"),
                            use_container_width=True, config={"displayModeBar": False})


# =================================================================
# Anomaly history: every saved detection, one day at a time (read-only).
# Today's alerts are resolved / dismissed from the Admin Dashboard.
# A fragment: changing the filters only redraws this section.
# =================================================================
HISTORY_TYPES = {"accident": ("🚨 Accident", "accident"), "flooded": ("🌊 Flooded Road", "flooded"),
                 "uncertain": ("❔ Uncertain", "uncertain")}
STATUS_OPTIONS = ["Active", "Resolved", "Dismissed"]


def history_table(rows):
    """Same table design as the Model Performance validation records."""
    times = pd.to_datetime(rows["detected_time"], errors="coerce")
    body = []
    for i, (r, t) in enumerate(zip(rows.itertuples(index=False), times), start=1):
        kind = str(r.anomaly_type).lower()
        label, cls = HISTORY_TYPES.get(kind, (str(r.anomaly_type).title(), "other"))
        conf = 0.0 if pd.isna(r.confidence_score) else float(r.confidence_score) * 100
        status = str(r.status).lower()
        body.append(
            f'<tr style="--i:{min(i, 12)}"><td>{i}</td>'
            f'<td>{t.strftime("%I:%M %p").lstrip("0") if pd.notna(t) else "—"}</td>'
            f"<td>{escape(str(r.camera_name))}</td>"
            f'<td><span class="ct-hist-type {cls}">{escape(label)}</span></td>'
            f'<td><div class="ct-tbar"><div class="ct-meter"><span style="width:{conf:.1f}%"></span></div>'
            f"<b>{conf:.0f}%</b></div></td>"
            f'<td><span class="ct-hist-status {escape(status)}">{escape(status.title())}</span></td></tr>'
        )
    return (
        '<div class="ct-table-wrap ct-hist-table"><table class="ct-table"><thead><tr>'
        "<th>NO.</th><th>TIME</th><th>LOCATION</th><th>ANOMALY</th><th>CONFIDENCE</th><th>STATUS</th>"
        f"</tr></thead><tbody>{''.join(body)}</tbody></table></div>"
    )


@st.fragment
def anomaly_history():
    with st.container(key="anomaly_history"):
        st.markdown(
            '<div class="ct-ws-head"><span class="ct-ws-kicker">◉ &nbsp; ANOMALY HISTORY</span>'
            '<span class="ct-ws-hint">Every saved detection · nothing is deleted</span></div>',
            unsafe_allow_html=True,
        )
        today = now_karachi().date()
        cameras = camera_list()
        date_col, cam_col, status_col = st.columns([1, 1.2, 2], vertical_alignment="bottom")
        with date_col:
            day = st.date_input("Date", value=today, max_value=today, format="DD/MM/YYYY", key="hist_day")
        with cam_col:
            cam = st.selectbox("Camera", [None, *cameras], key="hist_cam",
                               format_func=lambda i: "All cameras" if i is None else cameras[i])
        with status_col:
            status = st.segmented_control("Status", ["All", *STATUS_OPTIONS], default="All", key="res_hist_status")

        rows = alerts_on_day(day, cam)
        if rows is None:
            st.info("Anomaly logging isn't set up yet. Run backend/update_anomaly_status.py once.")
            return

        counts = rows["status"].value_counts()
        st.markdown(
            '<div class="ct-hist-chips">'
            f'<span><b>{len(rows)}</b> detection{"s" if len(rows) != 1 else ""}</span>'
            f'<span class="active"><b>{counts.get("active", 0)}</b> active</span>'
            f'<span class="resolved"><b>{counts.get("resolved", 0)}</b> resolved</span>'
            f'<span class="dismissed"><b>{counts.get("dismissed", 0)}</b> dismissed</span>'
            f'<span class="day">{day:%A, %d %B %Y}</span></div>',
            unsafe_allow_html=True,
        )

        if status and status != "All":
            rows = rows[rows["status"] == status.lower()]
        if rows.empty:
            st.markdown('<div class="ct-hist-empty">No detections for this selection.</div>', unsafe_allow_html=True)
            return
        st.markdown(history_table(rows), unsafe_allow_html=True)


divider()
anomaly_history()


# =================================================================
# Model information: short summary left, stats and per-class results right
# =================================================================
m = MODEL_METRICS
class_rows = "".join(
    '<div class="ct-mi-row">'
    f'<div class="ct-mi-name"><span class="ct-mi-dot" style="background:{style(name)["color"]}"></span>'
    f'{style(name)["title"].replace(" Road", "").replace(" Traffic", "")}</div>'
    f'<div class="ct-mi-num">{prec:.1f}%</div><div class="ct-mi-num">{rec:.1f}%</div>'
    f'<div class="ct-mi-bar"><i style="width:{rec}%;background:{style(name)["color"]}"></i></div>'
    "</div>"
    for name, (prec, rec) in m["per_class"].items()
)
divider()
st.markdown(
    '<section class="ct-mi">'
    '<div class="ct-ws-head"><span class="ct-ws-kicker">◉ &nbsp; MODEL INFORMATION</span>'
    f'<span class="ct-ws-hint">Evaluated on {m["test_images"]} held-out test images</span></div>'
    '<div class="ct-mi-layout">'

    '<div class="ct-mi-summary">'
    '<h3>Road scene classifier · <span>MobileNetV2</span></h3>'
    "<p>A <strong>MobileNetV2</strong> network, pretrained on ImageNet and <strong>fine-tuned in two phases</strong> "
    "on labelled road-scene frames taken from traffic videos. It reads a single image, or a video at "
    f"{SAMPLE_FPS} frames per second, and classifies the scene as an <strong>accident</strong>, "
    "a <strong>flooded road</strong> or <strong>normal traffic</strong>.</p>"
    f"<p>Any prediction below <strong>{CONFIDENCE_THRESHOLD:.0%} confidence</strong> is shown as "
    "<strong>Uncertain</strong> so an operator can check the footage. For videos, an anomaly is reported only "
    f"if it appears in at least {SUSTAINED_SHARE:.0%} of the frames.</p>"
    '<div class="ct-mi-facts"><span>224 × 224 RGB input</span><span>Split by source video</span>'
    "<span>Class-weighted training</span></div>"
    "</div>"

    "<div>"
    '<div class="ct-mi-cards">'
    f'<div class="ct-mi-card"><span>Test accuracy</span><strong class="gold">{m["accuracy"]:.1f}%</strong>'
    f'<small>{m["correct"]} of {m["test_images"]} correct</small></div>'
    f'<div class="ct-mi-card"><span>Macro F1</span><strong class="gold">{m["macro_f1"]:.1f}%</strong>'
    "<small>balanced across classes</small></div>"
    f'<div class="ct-mi-card"><span>Classes</span><strong>{len(m["per_class"])}</strong>'
    f'<small>{" · ".join(m["per_class"])}</small></div>'
    "</div>"
    '<div class="ct-mi-classes">'
    '<div class="ct-mi-row ct-mi-headrow"><div>Class</div><div>Precision</div><div>Recall</div><div></div></div>'
    f"{class_rows}</div>"
    "</div>"

    "</div></section>",
    unsafe_allow_html=True,
)

footer()
