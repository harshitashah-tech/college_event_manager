"""
utils/helpers.py
----------------
General-purpose utility functions.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone


def generate_transaction_ref() -> str:
    """Generate a unique transaction reference string."""
    return f"TXN-{uuid.uuid4().hex[:12].upper()}"


def format_currency(amount: float) -> str:
    """Format a number as Indian Rupees."""
    return f"₹{amount:,.2f}"


def format_datetime(dt_str: str | None) -> str:
    """Parse an ISO datetime string and return a human-friendly format."""
    if not dt_str:
        return "—"
    try:
        dt = datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
        return dt.strftime("%d %b %Y, %I:%M %p")
    except Exception:
        return dt_str


def format_date(dt_str: str | None) -> str:
    """Return only the date portion in a readable format."""
    if not dt_str:
        return "—"
    try:
        dt = datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
        return dt.strftime("%d %b %Y")
    except Exception:
        return dt_str


def is_event_upcoming(event_date_str: str) -> bool:
    """Return True if the event is in the future."""
    try:
        dt = datetime.fromisoformat(event_date_str.replace("Z", "+00:00"))
        return dt > datetime.now(tz=timezone.utc)
    except Exception:
        return False


def is_registration_open(event: dict) -> bool:
    """Check whether registration deadline hasn't passed."""
    deadline = event.get("registration_deadline")
    if not deadline:
        return is_event_upcoming(event["event_date"])
    try:
        dt = datetime.fromisoformat(deadline.replace("Z", "+00:00"))
        return dt > datetime.now(tz=timezone.utc)
    except Exception:
        return False


def truncate(text: str, max_len: int = 120) -> str:
    """Truncate text to max_len characters, appending '…'."""
    if not text:
        return ""
    return text if len(text) <= max_len else text[:max_len] + "…"


def status_badge(status: str) -> str:
    """Return a coloured HTML badge for a status string."""
    colours = {
        "pending":  ("#FFA500", "#FFF3CD"),
        "approved": ("#2E7D32", "#D4EDDA"),
        "rejected": ("#C62828", "#FADBD8"),
        "paid":     ("#1565C0", "#D0E4FF"),
        "failed":   ("#C62828", "#FADBD8"),
        "active":   ("#2E7D32", "#D4EDDA"),
    }
    fg, bg = colours.get(status.lower(), ("#555", "#EEE"))
    return (
        f"<span style='background:{bg};color:{fg};"
        f"padding:2px 10px;border-radius:12px;"
        f"font-size:0.78rem;font-weight:600;'>{status.capitalize()}</span>"
    )
