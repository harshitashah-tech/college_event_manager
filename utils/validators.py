"""
utils/validators.py
--------------------
Input validation helpers used across auth and forms.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone


def validate_required(value: str | None, field_name: str) -> str | None:
    """Return an error string if value is blank, else None."""
    if not value or not str(value).strip():
        return f"{field_name} is required."
    return None


def validate_email(email: str) -> str | None:
    """Basic email format validation."""
    pattern = r"^[\w.\-+]+@[\w\-]+\.[\w.]{2,}$"
    if not re.match(pattern, email):
        return "Please enter a valid email address."
    return None


def validate_password(password: str) -> str | None:
    """Enforce minimum 8 characters."""
    if len(password) < 8:
        return "Password must be at least 8 characters."
    return None


def validate_future_date(dt: datetime | None, field_name: str = "Date") -> str | None:
    """Ensure a datetime is in the future."""
    if dt is None:
        return f"{field_name} is required."
    now = datetime.now()
    # Strip tz info for comparison if needed
    if dt.tzinfo is not None:
        now = datetime.now(tz=timezone.utc)
    if dt <= now:
        return f"{field_name} must be in the future."
    return None


def validate_positive_number(value: float | None, field_name: str) -> str | None:
    """Ensure value is a non-negative number."""
    if value is None:
        return None  # Optional field
    if value < 0:
        return f"{field_name} cannot be negative."
    return None


def sanitize_text(text: str) -> str:
    """Strip leading/trailing whitespace and remove dangerous HTML characters."""
    text = text.strip()
    text = text.replace("<", "&lt;").replace(">", "&gt;")
    return text
