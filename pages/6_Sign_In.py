"""Chronos-Traffic administrator sign-in page."""
import streamlit as st

from backend.auth import verify_login
from utils.styles import load_css

st.set_page_config(
    page_title="Chronos-Traffic | Sign In",
    page_icon="🔐",
    layout="wide",
    initial_sidebar_state="collapsed",
)
load_css("main.css", "signin.css")

# Already signed in as admin: skip straight to the dashboard.
if st.session_state.get("authenticated") and (st.session_state.get("user") or {}).get("role") == "admin":
    st.switch_page("pages/7_Admin_Dashboard.py")


# ---------------------------------------------------------------
# Back to Home
# ---------------------------------------------------------------
if st.button("← Back to Home", key="back_home"):
    st.switch_page("Home.py")


# ---------------------------------------------------------------
# Centered card: header, form, messages
# A keyed container with a max width (in CSS) replaces the old 3-column layout,
# so it stays centered and full-width on phones.
# ---------------------------------------------------------------
with st.container(key="signin_wrap"):
    st.markdown(
        '<div class="signin-header">'
        '<div class="signin-badge"><span class="signin-lock"></span></div>'
        '<div class="signin-title">Chronos-Traffic</div>'
        '<div class="signin-sub">Administrator Sign In</div>'
        "</div>",
        unsafe_allow_html=True,
    )

    # Inside a form nothing reruns while typing; the page only reruns on submit.
    with st.form("login_form", border=False):
        username = st.text_input("Username", placeholder="Enter username", key="login_username")
        # type="password" has a built-in eye button that shows/hides the text instantly.
        password = st.text_input("Password", type="password", placeholder="Enter password", key="login_password")

        _, btn_col, _ = st.columns([1, 2, 1])
        with btn_col:
            submitted = st.form_submit_button("Sign In  →", type="primary", use_container_width=True)

    if submitted:
        if not username.strip() or not password:
            st.warning("Please enter both username and password.")
        else:
            with st.spinner("Signing in…"):
                user = verify_login(username.strip(), password)
            if user:
                st.session_state["authenticated"] = True
                st.session_state["user"] = user
                st.switch_page("pages/7_Admin_Dashboard.py")
            else:
                st.error("Invalid username or password.")

    st.markdown('<div class="signin-footer">🔒 Authorized personnel only</div>', unsafe_allow_html=True)
