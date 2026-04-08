"""
modules/events.py
-----------------
All database operations for Events and Registrations — MongoDB version.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

import streamlit as st

from config import STATUS_APPROVED, STATUS_PENDING
from database.mongo_client import get_db
from utils.helpers import format_datetime, format_currency, truncate, status_badge, is_registration_open
from utils.validators import validate_required, validate_future_date


# ═══════════════════════════════════════════════════════════════
#  CREATE / UPDATE / DELETE
# ═══════════════════════════════════════════════════════════════

def create_event(
    title: str,
    description: str,
    category: str,
    club_id: Optional[str],
    coordinator_id: str,
    event_date: datetime,
    registration_deadline: Optional[datetime],
    venue: str,
    max_participants: int,
    is_paid: bool,
    ticket_price: float,
    tags: list[str],
) -> dict | None:
    """
    Insert a new event document (status='pending', awaiting admin approval).

    Returns the created event dict or None on error.
    """
    db = get_db()
    now = datetime.utcnow().isoformat()
    doc = {
        "_id": str(uuid.uuid4()),
        "title": title.strip(),
        "description": description.strip(),
        "category": category,
        "club_id": club_id or None,
        "coordinator_id": coordinator_id,
        "event_date": event_date.isoformat(),
        "registration_deadline": registration_deadline.isoformat() if registration_deadline else None,
        "venue": venue.strip(),
        "max_participants": max_participants,
        "is_paid": is_paid,
        "ticket_price": ticket_price if is_paid else 0.0,
        "status": STATUS_PENDING,
        "banner_url": None,
        "tags": tags,
        "created_at": now,
        "updated_at": now,
    }
    try:
        db.events.insert_one(doc)
        return {**doc, "id": doc["_id"]}
    except Exception as exc:
        st.error(f"Failed to create event: {exc}")
        return None


def update_event(event_id: str, updates: dict) -> bool:
    """Update an existing event by id. Returns True on success."""
    db = get_db()
    updates["updated_at"] = datetime.utcnow().isoformat()
    try:
        db.events.update_one({"_id": event_id}, {"$set": updates})
        return True
    except Exception as exc:
        st.error(f"Update failed: {exc}")
        return False


def delete_event(event_id: str) -> bool:
    """Hard-delete an event and its registrations. Returns True on success."""
    db = get_db()
    try:
        db.events.delete_one({"_id": event_id})
        db.registrations.delete_many({"event_id": event_id})
        return True
    except Exception as exc:
        st.error(f"Delete failed: {exc}")
        return False


def approve_event(event_id: str) -> bool:
    """Set event status to 'approved'."""
    return update_event(event_id, {"status": "approved"})


def reject_event(event_id: str) -> bool:
    """Set event status to 'rejected'."""
    return update_event(event_id, {"status": "rejected"})


# ═══════════════════════════════════════════════════════════════
#  QUERIES
# ═══════════════════════════════════════════════════════════════

def _enrich_event(event: dict, db) -> dict:
    """Attach club name and coordinator name to an event document."""
    event = {**event, "id": event["_id"]}
    if event.get("club_id"):
        club = db.clubs.find_one({"_id": event["club_id"]}, {"name": 1})
        event["clubs"] = {"name": club["name"]} if club else None
    else:
        event["clubs"] = None

    coord = db.users.find_one({"_id": event.get("coordinator_id")}, {"full_name": 1})
    event["users"] = {"full_name": coord["full_name"]} if coord else None
    return event


def get_all_events(status: Optional[str] = None) -> list[dict]:
    """Fetch events, optionally filtered by status."""
    db = get_db()
    try:
        query = {}
        if status:
            query["status"] = status
        raw = list(db.events.find(query).sort("event_date", 1))
        return [_enrich_event(e, db) for e in raw]
    except Exception as exc:
        st.error(f"Failed to load events: {exc}")
        return []


def get_events_by_coordinator(coordinator_id: str) -> list[dict]:
    """Fetch all events created by a coordinator."""
    db = get_db()
    try:
        raw = list(db.events.find({"coordinator_id": coordinator_id}).sort("created_at", -1))
        return [{**e, "id": e["_id"]} for e in raw]
    except Exception as exc:
        st.error(f"Failed to load events: {exc}")
        return []


def get_event_by_id(event_id: str) -> dict | None:
    """Fetch a single event by its UUID."""
    db = get_db()
    try:
        doc = db.events.find_one({"_id": event_id})
        return {**doc, "id": doc["_id"]} if doc else None
    except Exception:
        return None


def get_participants(event_id: str) -> list[dict]:
    """Fetch all non-cancelled registrations for an event with user info."""
    db = get_db()
    try:
        regs = list(db.registrations.find({"event_id": event_id, "cancelled": False}))
        result = []
        for reg in regs:
            user = db.users.find_one(
                {"_id": reg["user_id"]},
                {"full_name": 1, "email": 1, "department": 1, "year_of_study": 1},
            )
            result.append({
                **reg,
                "id": reg["_id"],
                "users": {**user, "id": user["_id"]} if user else None,
            })
        return result
    except Exception as exc:
        st.error(f"Failed to fetch participants: {exc}")
        return []


# ═══════════════════════════════════════════════════════════════
#  REGISTRATIONS
# ═══════════════════════════════════════════════════════════════

def is_registered(event_id: str, user_id: str) -> bool:
    """Check if a user is currently registered (not cancelled)."""
    db = get_db()
    try:
        return db.registrations.find_one(
            {"event_id": event_id, "user_id": user_id, "cancelled": False}
        ) is not None
    except Exception:
        return False


def register_for_event(event_id: str, user_id: str) -> dict | None:
    """
    Register a user for an event.

    Returns the new registration dict, or None if already registered / error.
    """
    db = get_db()

    if is_registered(event_id, user_id):
        st.warning("You are already registered for this event.")
        return None

    event = get_event_by_id(event_id)
    if not event:
        st.error("Event not found.")
        return None

    # Check capacity
    if event.get("max_participants", 0) > 0:
        count = db.registrations.count_documents({"event_id": event_id, "cancelled": False})
        if count >= event["max_participants"]:
            st.error("This event is fully booked.")
            return None

    now = datetime.utcnow().isoformat()
    reg_doc = {
        "_id": str(uuid.uuid4()),
        "event_id": event_id,
        "user_id": user_id,
        "registered_at": now,
        "cancelled": False,
        "cancelled_at": None,
    }

    try:
        db.registrations.insert_one(reg_doc)
        registration = {**reg_doc, "id": reg_doc["_id"]}

        # Auto-create payment record if paid event
        if event.get("is_paid"):
            from modules.payments import create_payment_record
            create_payment_record(
                registration_id=registration["id"],
                user_id=user_id,
                event_id=event_id,
                amount=event.get("ticket_price", 0.0),
            )

        # Send confirmation notification
        from modules.notifications import send_notification
        send_notification(
            user_id=user_id,
            title="Registration Confirmed 🎉",
            message=f"You've successfully registered for '{event['title']}'.",
            notif_type="success",
            related_event_id=event_id,
        )

        return registration
    except Exception as exc:
        st.error(f"Registration failed: {exc}")
        return None


def cancel_registration(event_id: str, user_id: str) -> bool:
    """Soft-cancel a user's registration (sets cancelled=True)."""
    db = get_db()
    try:
        db.registrations.update_one(
            {"event_id": event_id, "user_id": user_id},
            {"$set": {"cancelled": True, "cancelled_at": datetime.utcnow().isoformat()}},
        )
        return True
    except Exception as exc:
        st.error(f"Cancellation failed: {exc}")
        return False


def get_user_registrations(user_id: str) -> list[dict]:
    """Fetch all active registrations for a user, including event details."""
    db = get_db()
    try:
        regs = list(db.registrations.find({"user_id": user_id, "cancelled": False}).sort("registered_at", -1))
        result = []
        for reg in regs:
            event = db.events.find_one({"_id": reg["event_id"]})
            result.append({
                **reg,
                "id": reg["_id"],
                "events": {**event, "id": event["_id"]} if event else None,
            })
        return result
    except Exception as exc:
        st.error(f"Failed to load registrations: {exc}")
        return []


# ═══════════════════════════════════════════════════════════════
#  STREAMLIT UI COMPONENTS
# ═══════════════════════════════════════════════════════════════

def render_event_form(
    coordinator_id: str,
    existing: dict | None = None,
) -> None:
    """
    Render the Create / Edit event form.

    Parameters
    ----------
    coordinator_id : str
    existing : dict | None
        If provided, pre-fills form for editing.
    """
    from config import EVENT_CATEGORIES
    from modules.clubs import get_clubs_by_coordinator

    clubs = get_clubs_by_coordinator(coordinator_id)
    club_options = {c["name"]: c["id"] for c in clubs if c.get("status") == "approved"}
    club_options["(No club)"] = None

    mode = "Edit" if existing else "Create"

    with st.form(f"{mode.lower()}_event_form"):
        st.subheader(f"{'✏️ Edit' if existing else '➕ Create'} Event")

        col1, col2 = st.columns(2)
        with col1:
            title = st.text_input(
                "Event Title *",
                value=existing.get("title", "") if existing else "",
            )
            category = st.selectbox(
                "Category *",
                EVENT_CATEGORIES,
                index=EVENT_CATEGORIES.index(existing["category"])
                if existing and existing.get("category") in EVENT_CATEGORIES
                else 0,
            )
            venue = st.text_input(
                "Venue",
                value=existing.get("venue", "") if existing else "",
            )
            max_p = st.number_input(
                "Max Participants (0 = unlimited)",
                min_value=0,
                value=existing.get("max_participants", 0) if existing else 0,
            )
        with col2:
            club_name = st.selectbox("Hosting Club", list(club_options.keys()))
            event_date = st.date_input("Event Date *")
            event_time = st.time_input("Event Time")
            reg_deadline = st.date_input("Registration Deadline (optional)")

        description = st.text_area(
            "Description",
            value=existing.get("description", "") if existing else "",
            height=100,
        )

        col3, col4 = st.columns(2)
        with col3:
            is_paid = st.checkbox(
                "Paid Event",
                value=existing.get("is_paid", False) if existing else False,
            )
        with col4:
            ticket_price = st.number_input(
                "Ticket Price (₹)",
                min_value=0.0,
                value=float(existing.get("ticket_price", 0)) if existing else 0.0,
                disabled=not is_paid,
            )

        tags_input = st.text_input(
            "Tags (comma-separated)",
            value=", ".join(existing.get("tags") or []) if existing else "",
        )

        submitted = st.form_submit_button(
            f"{'Update' if existing else 'Submit for Approval'}",
            use_container_width=True,
        )

    if submitted:
        event_dt = datetime.combine(event_date, event_time)
        reg_dt = datetime.combine(reg_deadline, datetime.min.time()) if reg_deadline else None
        tags = [t.strip() for t in tags_input.split(",") if t.strip()]

        err = validate_required(title, "Event title")
        if err:
            st.error(err)
            return

        if existing:
            success = update_event(existing["id"], {
                "title": title,
                "description": description,
                "category": category,
                "club_id": club_options[club_name],
                "event_date": event_dt.isoformat(),
                "registration_deadline": reg_dt.isoformat() if reg_dt else None,
                "venue": venue,
                "max_participants": int(max_p),
                "is_paid": is_paid,
                "ticket_price": ticket_price if is_paid else 0.0,
                "tags": tags,
            })
            if success:
                st.success("Event updated successfully!")
        else:
            result = create_event(
                title=title,
                description=description,
                category=category,
                club_id=club_options[club_name],
                coordinator_id=coordinator_id,
                event_date=event_dt,
                registration_deadline=reg_dt,
                venue=venue,
                max_participants=int(max_p),
                is_paid=is_paid,
                ticket_price=ticket_price,
                tags=tags,
            )
            if result:
                st.success("Event submitted for admin approval! 🎉")
