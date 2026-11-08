from pathlib import Path
import streamlit as st

ROOT = Path(__file__).resolve().parent.parent


def load_css(*names: str) -> None:
    for name in names:
        path = ROOT / 'Assets' / 'styles' / name
        st.markdown(f'<style>{path.read_text(encoding="utf-8")}</style>', unsafe_allow_html=True)
