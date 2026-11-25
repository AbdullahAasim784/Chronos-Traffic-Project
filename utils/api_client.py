"""FastAPI client for the public Traffic Dashboard."""
import requests
import streamlit as st

from utils.config import API_BASE_URL, API_TIMEOUT

# Errors to catch around fetch(): backend down, timeout, bad JSON.
API_ERRORS = (requests.RequestException, ValueError)


def api_get(endpoint, params=None):
    response = requests.get(f"{API_BASE_URL}{endpoint}", params=params, timeout=API_TIMEOUT)
    response.raise_for_status()
    return response.json()


@st.cache_data(ttl=300, show_spinner=False)
def fetch(endpoint, **params):
    """Cached API call. Reruns reuse the response instead of asking the backend again."""
    return api_get(endpoint, params or None)
