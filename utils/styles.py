"""Loads the stylesheets in Assets/styles."""
import streamlit as st

from utils.config import STYLES_DIR


def load_css(*names, public=False):
    """Inject the given stylesheets as ONE <style> block.

    One block instead of one per file: each st.markdown adds a small vertical gap,
    so a single block keeps page spacing the same no matter how many files a page loads.
    public=True adds the .ct-public-page marker, which makes main.css hide the sidebar and toolbar.
    """
    css = "\n".join((STYLES_DIR / name).read_text(encoding="utf-8") for name in names)
    marker = '<span class="ct-public-page"></span>' if public else ""
    st.markdown(f"<style>{css}</style>{marker}", unsafe_allow_html=True)
