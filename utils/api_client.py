
import requests

API_BASE_URL = "http://127.0.0.1:8000"


def api_get(endpoint, params=None):
    response = requests.get(
        f"{API_BASE_URL}{endpoint}",
        params=params,
        timeout=15
    )

    response.raise_for_status()

    return response.json()
