from pathlib import Path
import streamlit as st

ROOT = Path(__file__).resolve().parent.parent


def load_css(*names: str) -> None:
    """Inject the given stylesheets from Assets/styles as ONE <style> block.

    One block instead of one per file: each st.markdown adds a small vertical gap,
    so a single block keeps page spacing the same no matter how many files a page loads.
    """
    css = "\n".join((ROOT / "Assets" / "styles" / name).read_text(encoding="utf-8") for name in names)
    st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)
