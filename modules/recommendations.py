"""
modules/recommendations.py
--------------------------
Rule-based event recommendation engine.

Scoring Logic
-------------
For each upcoming approved event:
  +3 if the event's club matches one of the user's clubs
  +2 if the event's category matches a category the user has registered for before
  +1 for each previous registration in the same category (frequency bonus)
  +1 if event is popular (>= 5 registrations)

Events are sorted by score descending.
"""

from __future__ import annotations

from collections import Counter

import streamlit as st

from config import (
    REC_CLUB_MATCH_SCORE,
    REC_CATEGORY_MATCH_SCORE,
    REC_PAST_REGISTRATION_SCORE,
    STATUS_APPROVED,
)
from database.mongo_client import get_db
from modules.events import get_user_registrations, is_registered
from modules.clubs import get_user_clubs
from utils.helpers import is_event_upcoming


# ═══════════════════════════════════════════════════════════════
#  ENGINE
# ═══════════════════════════════════════════════════════════════

def _get_user_club_ids(user_id: str) -> set[str]:
    """Return a set of club IDs the user is approved in."""
    memberships = get_user_clubs(user_id)
    return {m["clubs"]["id"] for m in memberships if m.get("clubs")}


def _get_user_category_history(user_id: str) -> Counter:
    """
    Return a Counter of event categories from the user's past registrations.
    e.g. {'Technical': 3, 'Cultural': 1}
    """
    registrations = get_user_registrations(user_id)
    categories = []
    for reg in registrations:
        event = reg.get("events") or {}
        cat = event.get("category")
        if cat:
            categories.append(cat)
    return Counter(categories)


def _get_registration_counts() -> dict[str, int]:
    """Return a dict mapping event_id → participant count (approved events only)."""
    db = get_db()
    try:
        pipeline = [
            {"$match": {"cancelled": False}},
            {"$group": {"_id": "$event_id", "count": {"$sum": 1}}}
        ]
        results = list(db.registrations.aggregate(pipeline))
        return {r["_id"]: r["count"] for r in results}
    except Exception:
        return {}


def get_recommendations(user_id: str, limit: int = 6) -> list[dict]:
    """
    Generate a scored list of recommended upcoming events for a user.

    Parameters
    ----------
    user_id : str
    limit : int
        Max number of recommendations to return.

    Returns
    -------
    list[dict]
        Events sorted by recommendation score, each with a '_score' key.
    """
    db = get_db()

    # ── Fetch all approved, upcoming events ───────────────────
    try:
        raw_events = list(db.events.find({"status": STATUS_APPROVED}))
        all_events = [{**e, "id": e["_id"]} for e in raw_events]
    except Exception:
        return []

    upcoming = [e for e in all_events if is_event_upcoming(e["event_date"])]

    if not upcoming:
        return []

    # ── Build user profile ────────────────────────────────────
    user_club_ids = _get_user_club_ids(user_id)
    category_history = _get_user_category_history(user_id)
    reg_counts = _get_registration_counts()

    scored = []
    for event in upcoming:
        # Skip already-registered events
        if is_registered(event["id"], user_id):
            continue

        score = 0

        # Club match
        if event.get("club_id") and event["club_id"] in user_club_ids:
            score += REC_CLUB_MATCH_SCORE

        # Category match
        cat = event.get("category", "")
        if cat in category_history:
            score += REC_CATEGORY_MATCH_SCORE
            # Frequency bonus (capped at 3)
            freq_bonus = min(category_history[cat], 3) * REC_PAST_REGISTRATION_SCORE
            score += freq_bonus

        # Popularity bonus
        if reg_counts.get(event["id"], 0) >= 5:
            score += 1

        event["_score"] = score
        scored.append(event)

    # Sort by score desc, then by event_date asc
    scored.sort(key=lambda e: (-e["_score"], e["event_date"]))

    return scored[:limit]


# ═══════════════════════════════════════════════════════════════
#  UI COMPONENT
# ═══════════════════════════════════════════════════════════════

def render_recommendations(user_id: str) -> None:
    """Render the recommended events section on student dashboard."""
    from utils.styling import section_header, empty_state
    from utils.helpers import format_date, truncate, format_currency

    section_header(
        "✨ Recommended For You",
        "Based on your clubs and past registrations",
    )

    recs = get_recommendations(user_id)

    if not recs:
        empty_state("Register for events and join clubs to get personalised recommendations!")
        return

    cols = st.columns(min(len(recs), 3))
    for i, event in enumerate(recs[:6]):
        col = cols[i % 3]
        with col:
            score = event.get("_score", 0)
            price_str = (
                format_currency(event.get("ticket_price", 0))
                if event.get("is_paid")
                else "Free"
            )
            st.markdown(
                f"""
                <div class='es-event-card' style='position:relative;'>
                    <div class='es-event-category'>{event.get('category','')}</div>
                    {"<span style='position:absolute;top:12px;right:12px;background:#889FC4;color:#fff;"
                     "border-radius:12px;padding:2px 8px;font-size:0.7rem;font-weight:700;'>"
                     f"⭐ {score}</span>" if score > 0 else ""}
                    <h4 class='es-event-title'>{event['title']}</h4>
                    <p class='es-event-desc'>{truncate(event.get('description',''), 80)}</p>
                    <div class='es-event-meta'>
                        <span>📅 {format_date(event['event_date'])}</span>
                        <span>{'💰 ' + price_str if event.get('is_paid') else '🆓 Free'}</span>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            if st.button("Register →", key=f"rec_reg_{event['id']}_{i}"):
                from modules.events import register_for_event
                result = register_for_event(event["id"], user_id)
                if result:
                    st.success("Registered! 🎉")
                    st.rerun()
