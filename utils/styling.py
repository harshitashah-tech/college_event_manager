"""
utils/styling.py
----------------
CSS injection and reusable UI component wrappers for Streamlit.
"""

from __future__ import annotations

from contextlib import contextmanager
import streamlit as st


# ── Brand colours (mirrored here for Python-side usage) ─────────────────────
PRIMARY   = "#A6BEE0"
SECONDARY = "#889FC4"
ACCENT    = "#7E8BB1"
BG        = "#E8E8E3"
CARD_BG   = "#E2E1DE"
DARK      = "#2C3E6B"


def inject_global_css() -> None:
    """Inject the full custom CSS into the Streamlit page once."""
    with open("assets/styles.css", "r") as f:
        css = f.read()
    st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)


@contextmanager
def card_container(key: str = ""):
    """Wrap content in a styled card div."""
    st.markdown(f"<div class='es-card' id='card-{key}'>", unsafe_allow_html=True)
    yield
    st.markdown("</div>", unsafe_allow_html=True)


def section_header(title: str, subtitle: str = "") -> None:
    """Render a section heading with optional subtitle."""
    st.markdown(
        f"<div class='es-section-header'>"
        f"<h3>{title}</h3>"
        f"{'<p>' + subtitle + '</p>' if subtitle else ''}"
        f"</div>",
        unsafe_allow_html=True,
    )


def metric_card(label: str, value: str, icon: str = "📊", delta: str = "") -> None:
    """Render a stat metric card."""
    delta_html = f"<span class='es-delta'>{delta}</span>" if delta else ""
    st.markdown(
        f"""
        <div class='es-metric-card'>
            <div class='es-metric-icon'>{icon}</div>
            <div class='es-metric-value'>{value}</div>
            <div class='es-metric-label'>{label}</div>
            {delta_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


def event_card(event: dict, show_actions: bool = False) -> None:
    """Render a single event card."""
    from utils.helpers import format_date, truncate, status_badge, format_currency

    is_paid = event.get("is_paid", False)
    price_html = (
        f"<span class='es-price-tag'>{format_currency(event.get('ticket_price', 0))}</span>"
        if is_paid
        else "<span class='es-free-tag'>FREE</span>"
    )

    st.markdown(
        f"""
        <div class='es-event-card'>
            <div class='es-event-category'>{event.get('category','General')}</div>
            <h4 class='es-event-title'>{event.get('title','')}</h4>
            <p class='es-event-desc'>{truncate(event.get('description',''), 100)}</p>
            <div class='es-event-meta'>
                <span>📅 {format_date(event.get('event_date'))}</span>
                <span>📍 {event.get('venue') or 'TBA'}</span>
                {price_html}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def notification_badge(count: int) -> str:
    """Return HTML for an unread-notification badge."""
    if count == 0:
        return ""
    return (
        f"<span style='background:#E74C3C;color:#fff;"
        f"border-radius:50%;padding:1px 7px;"
        f"font-size:0.7rem;margin-left:6px;'>{count}</span>"
    )


def divider() -> None:
    """Thin decorative divider."""
    st.markdown("<hr class='es-divider'>", unsafe_allow_html=True)


def empty_state(message: str = "Nothing here yet 🌱") -> None:
    """Friendly empty-state message."""
    st.markdown(
        f"<div class='es-empty-state'>{message}</div>",
        unsafe_allow_html=True,
    )
