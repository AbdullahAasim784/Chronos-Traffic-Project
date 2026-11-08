"""Admin-only access check and sidebar navigation. Call both at the top of every admin page."""
import html

import streamlit as st

from utils.styles import load_css

# Only these pages appear in the admin sidebar.
ADMIN_PAGES = [
    ("pages/7_Admin_Dashboard.py", "Admin Dashboard", "📊"),
    ("pages/3_Model_Performance.py", "Model Performance", "🎯"),
    ("pages/2_Historical_Analysis.py", "Historical Data", "🗄️"),
    ("pages/4_Road_Anomaly_Detection.py", "Road Anomaly Detection", "🚨"),
]


def require_admin():
    """Block the page unless an admin is logged in."""
    user = st.session_state.get("user") or {}
    if not st.session_state.get("authenticated") or user.get("role") != "admin":
        st.error("Administrator sign-in required.")
        if st.button("Go to Sign In"):
            st.switch_page("pages/6_Sign_In.py")
        st.stop()


def admin_sidebar():
    """Draw the admin navigation in the sidebar."""
    load_css("admin_nav.css")
    user = st.session_state.get("user") or {}
    name = html.escape(str(user.get("username") or user.get("name") or "Administrator"))

    with st.sidebar:
        st.markdown(
            '<div class="ct-side-brand">'
            '<div class="ct-side-logo">🚦</div>'
            '<div><div class="ct-side-name">Chronos-Traffic</div>'
            '<div class="ct-side-role">ADMIN PANEL</div></div>'
            "</div>"
            '<div class="ct-side-section">NAVIGATION</div>',
            unsafe_allow_html=True,
        )
        for path, label, icon in ADMIN_PAGES:
            st.page_link(path, label=label, icon=icon)

        st.markdown(
            '<div class="ct-side-user">'
            f'<div class="ct-side-avatar">{name[:1].upper()}</div>'
            f'<div><div class="ct-side-user-name">{name}</div>'
            '<div class="ct-side-user-role"><span></span>Signed in · Admin</div></div>'
            "</div>",
            unsafe_allow_html=True,
        )
