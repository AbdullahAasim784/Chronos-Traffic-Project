"""Number, time and label formatting used across all pages."""
from datetime import datetime


def _missing(value):
    return value is None or value != value   # None or NaN


def fmt(value):
    """Whole number with thousands separators: 1234.6 -> '1,235'. Missing -> '—'."""
    return "—" if _missing(value) else f"{round(value):,}"


def num(value, digits=1):
    """Decimal number with thousands separators: num(3.14159, 2) -> '3.14'. Missing -> '—'."""
    return "—" if _missing(value) else f"{value:,.{digits}f}"


def clock(dt):
    """12-hour time without a leading zero: 09:30 -> '9:30 AM'."""
    return dt.strftime("%I:%M %p").lstrip("0")


def hour_label(hour):
    """Hour of day (0-23) -> '5:00 PM'."""
    return clock(datetime(2000, 1, 1, int(hour)))


def level(congestion):
    """Congestion label -> CSS suffix: low / medium / high / na."""
    key = str(congestion or "").strip().lower()
    if key == "low":
        return "low"
    if key in ("medium", "moderate"):
        return "medium"
    if key == "high":
        return "high"
    return "na"
