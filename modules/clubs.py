"""
modules/clubs.py
----------------
Database operations and UI for Clubs and Club Members — MongoDB version.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

import streamlit as st

from database.mongo_client import get_db
from utils.validators import validate_required


# ═══════════════════════════════════════════════════════════════
#  CRUD
# ═══════════════════════════════════════════════════════════════

def create_club(
    name: str,
    description: str,
    category: str,
    coordinator_id: str,
) -> dict | None:
    """Create a new club (status='pending')."""
    db = get_db()
    now = datetime.utcnow().isoformat()
    doc = {
        "_id": str(uuid.uuid4()),
        "name": name.strip(),
        "description": description.strip(),
        "category": category,
        "coordinator_id": coordinator_id,
        "status": "pending",
        "logo_url": None,
        "created_at": now,
        "updated_at": now,
    }
    try:
        db.clubs.insert_one(doc)
        return {**doc, "id": doc["_id"]}
    except Exception as exc:
        st.error(f"Failed to create club: {exc}")
        return None


def update_club(club_id: str, updates: dict) -> bool:
    db = get_db()
    updates["updated_at"] = datetime.utcnow().isoformat()
    try:
        db.clubs.update_one({"_id": club_id}, {"$set": updates})
        return True
    except Exception as exc:
        st.error(f"Club update failed: {exc}")
        return False


def approve_club(club_id: str) -> bool:
    return update_club(club_id, {"status": "approved"})


def reject_club(club_id: str) -> bool:
    return update_club(club_id, {"status": "rejected"})


# ═══════════════════════════════════════════════════════════════
#  QUERIES
# ═══════════════════════════════════════════════════════════════

def get_all_clubs(status: Optional[str] = None) -> list[dict]:
    """Return clubs; optionally filter by status."""
    db = get_db()
    try:
        query = {}
        if status:
            query["status"] = status
        raw = list(db.clubs.find(query).sort("name", 1))
        result = []
        for club in raw:
            club = {**club, "id": club["_id"]}
            coord = db.users.find_one({"_id": club.get("coordinator_id")}, {"full_name": 1})
            club["users"] = {"full_name": coord["full_name"]} if coord else None
            result.append(club)
        return result
    except Exception as exc:
        st.error(f"Failed to load clubs: {exc}")
        return []


def get_clubs_by_coordinator(coordinator_id: str) -> list[dict]:
    db = get_db()
    try:
        raw = list(db.clubs.find({"coordinator_id": coordinator_id}))
        return [{**c, "id": c["_id"]} for c in raw]
    except Exception as exc:
        st.error(f"Failed to load clubs: {exc}")
        return []


def get_club_by_id(club_id: str) -> dict | None:
    db = get_db()
    try:
        doc = db.clubs.find_one({"_id": club_id})
        return {**doc, "id": doc["_id"]} if doc else None
    except Exception:
        return None


def get_members(club_id: str) -> list[dict]:
    """Return approved members of a club with user info."""
    db = get_db()
    try:
        memberships = list(db.club_members.find({"club_id": club_id, "status": "approved"}))
        result = []
        for m in memberships:
            user = db.users.find_one(
                {"_id": m["user_id"]},
                {"full_name": 1, "email": 1, "department": 1, "year_of_study": 1},
            )
            result.append({
                **m,
                "id": m["_id"],
                "users": {**user, "id": user["_id"]} if user else None,
            })
        return result
    except Exception as exc:
        st.error(f"Failed to fetch members: {exc}")
        return []


def get_pending_members(club_id: str) -> list[dict]:
    """Return pending membership requests for a club."""
    db = get_db()
    try:
        memberships = list(db.club_members.find({"club_id": club_id, "status": "pending"}))
        result = []
        for m in memberships:
            user = db.users.find_one(
                {"_id": m["user_id"]},
                {"full_name": 1, "email": 1, "department": 1},
            )
            result.append({
                **m,
                "id": m["_id"],
                "users": {**user, "id": user["_id"]} if user else None,
            })
        return result
    except Exception:
        return []


def get_user_clubs(user_id: str) -> list[dict]:
    """Return clubs a user has been approved into."""
    db = get_db()
    try:
        memberships = list(db.club_members.find({"user_id": user_id, "status": "approved"}))
        result = []
        for m in memberships:
            club = db.clubs.find_one({"_id": m["club_id"]})
            result.append({
                **m,
                "id": m["_id"],
                "clubs": {**club, "id": club["_id"]} if club else None,
            })
        return result
    except Exception:
        return []


def get_user_membership_status(club_id: str, user_id: str) -> str | None:
    """Return the membership status of a user for a club, or None if not applied."""
    db = get_db()
    try:
        doc = db.club_members.find_one({"club_id": club_id, "user_id": user_id})
        return doc["status"] if doc else None
    except Exception:
        return None


# ═══════════════════════════════════════════════════════════════
#  MEMBERSHIP ACTIONS
# ═══════════════════════════════════════════════════════════════

def apply_to_club(club_id: str, user_id: str) -> bool:
    """Student applies to join a club."""
    db = get_db()
    existing = get_user_membership_status(club_id, user_id)
    if existing:
        st.warning(f"You already have a '{existing}' application for this club.")
        return False
    try:
        db.club_members.insert_one({
            "_id": str(uuid.uuid4()),
            "club_id": club_id,
            "user_id": user_id,
            "status": "pending",
            "joined_at": datetime.utcnow().isoformat(),
        })
        return True
    except Exception as exc:
        st.error(f"Application failed: {exc}")
        return False


def approve_member(membership_id: str) -> bool:
    db = get_db()
    try:
        db.club_members.update_one({"_id": membership_id}, {"$set": {"status": "approved"}})
        return True
    except Exception:
        return False


def reject_member(membership_id: str) -> bool:
    db = get_db()
    try:
        db.club_members.update_one({"_id": membership_id}, {"$set": {"status": "rejected"}})
        return True
    except Exception:
        return False


def remove_member(club_id: str, user_id: str) -> bool:
    db = get_db()
    try:
        db.club_members.delete_one({"club_id": club_id, "user_id": user_id})
        return True
    except Exception:
        return False


# ═══════════════════════════════════════════════════════════════
#  UI COMPONENTS
# ═══════════════════════════════════════════════════════════════

def render_club_card(club: dict, user_id: str | None = None, user_role: str = "student") -> None:
    """Render a single club card with optional join button."""
    from utils.helpers import truncate, status_badge

    col1, col2 = st.columns([4, 1])
    with col1:
        st.markdown(
            f"<div style='font-weight:700;font-size:1.05rem;color:#2C3E6B;'>{club['name']}</div>",
            unsafe_allow_html=True,
        )
        st.markdown(
            f"<div style='font-size:0.85rem;color:#666;margin-bottom:0.3rem;'>"
            f"{truncate(club.get('description', ''), 90)}</div>",
            unsafe_allow_html=True,
        )
        if club.get("category"):
            st.markdown(
                f"<span style='background:#A6BEE0;color:#2C3E6B;padding:2px 10px;"
                f"border-radius:12px;font-size:0.75rem;font-weight:600;'>"
                f"{club['category']}</span>",
                unsafe_allow_html=True,
            )

    with col2:
        if user_id and user_role == "student":
            status = get_user_membership_status(club["id"], user_id)
            if status == "approved":
                st.success("✓ Member")
            elif status == "pending":
                st.info("Pending")
            else:
                if st.button("Join", key=f"join_{club['id']}"):
                    if apply_to_club(club["id"], user_id):
                        st.success("Application submitted!")
                        st.rerun()

    st.markdown("<hr style='margin:0.6rem 0;border-color:rgba(166,190,224,0.3);'>", unsafe_allow_html=True)


def render_create_club_form(coordinator_id: str) -> None:
    """Render form to create a new club."""
    categories = ["Technical", "Cultural", "Sports", "Arts", "Academic", "Social", "Other"]
    with st.form("create_club_form"):
        st.subheader("➕ Create New Club")
        name = st.text_input("Club Name *")
        description = st.text_area("Description", height=80)
        category = st.selectbox("Category", categories)
        submitted = st.form_submit_button("Submit for Approval", use_container_width=True)

    if submitted:
        err = validate_required(name, "Club name")
        if err:
            st.error(err)
            return
        result = create_club(name, description, category, coordinator_id)
        if result:
            st.success("Club submitted for admin approval! 🎉")
