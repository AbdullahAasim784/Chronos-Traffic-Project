"""Admin-only access check and sidebar navigation. Call both at the top of every admin page."""
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


def admin_sidebar(load_styles=True):
    """Draw the admin navigation in the sidebar.

    setup_admin_page() already loads admin_nav.css together with the page CSS, so it passes load_styles=False.
    """
    if load_styles:
        load_css("admin_nav.css")

    with st.sidebar:
        # To add your logo later, put <img class="ct-side-logo" src="..."> before the name block.
        st.markdown(
            '<div class="ct-side-brand">'
            '<div><div class="ct-side-name">Chronos-Traffic</div>'
            '<div class="ct-side-role">ADMIN PANEL</div></div>'
            "</div>"
            '<div class="ct-side-section">NAVIGATION</div>',
            unsafe_allow_html=True,
        )
        for path, label, icon in ADMIN_PAGES:
            st.page_link(path, label=label, icon=icon)

        # App info, pinned to the bottom of the sidebar by admin_nav.css.
        with st.container(key="ct_side_footer"):
            st.markdown(
                '<div class="ct-side-footer">'
                '<div class="ct-side-version">Version 2.0</div>'
                '<div class="ct-side-copy">© 2026 Bahria University<br>Computer Science Department</div>'
                "</div>",
                unsafe_allow_html=True,
            )
