"""
modules/notifications.py
------------------------
Create, fetch, and mark-as-read notifications — MongoDB version.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

import streamlit as st

from database.mongo_client import get_db
from utils.helpers import format_datetime


# ═══════════════════════════════════════════════════════════════
#  CRUD
# ═══════════════════════════════════════════════════════════════

def send_notification(
    user_id: str,
    title: str,
    message: str,
    notif_type: str = "info",
    related_event_id: Optional[str] = None,
) -> bool:
    """
    Insert a notification document for a specific user.

    Parameters
    ----------
    user_id : str
    title : str
    message : str
    notif_type : str
        One of: 'info', 'success', 'warning', 'error'
    related_event_id : str | None

    Returns
    -------
    bool
    """
    db = get_db()
    try:
        db.notifications.insert_one({
            "_id": str(uuid.uuid4()),
            "user_id": user_id,
            "title": title,
            "message": message,
            "type": notif_type,
            "related_event_id": related_event_id,
            "is_read": False,
            "created_at": datetime.utcnow().isoformat(),
        })
        return True
    except Exception as exc:
        print(f"[Notification error] {exc}")
        return False


def broadcast_notification(
    user_ids: list[str],
    title: str,
    message: str,
    notif_type: str = "info",
    related_event_id: Optional[str] = None,
) -> int:
    """Send the same notification to multiple users. Returns count sent."""
    count = 0
    for uid in user_ids:
        if send_notification(uid, title, message, notif_type, related_event_id):
            count += 1
    return count


def get_user_notifications(user_id: str, unread_only: bool = False) -> list[dict]:
    """Fetch notifications for a user, newest first."""
    db = get_db()
    try:
        query: dict = {"user_id": user_id}
        if unread_only:
            query["is_read"] = False
        raw = list(db.notifications.find(query).sort("created_at", -1))
        return [{**n, "id": n["_id"]} for n in raw]
    except Exception as exc:
        st.error(f"Failed to load notifications: {exc}")
        return []


def get_unread_count(user_id: str) -> int:
    """Return the number of unread notifications for a user."""
    db = get_db()
    try:
        return db.notifications.count_documents({"user_id": user_id, "is_read": False})
    except Exception:
        return 0


def mark_as_read(notification_id: str) -> bool:
    db = get_db()
    try:
        db.notifications.update_one({"_id": notification_id}, {"$set": {"is_read": True}})
        return True
    except Exception:
        return False


def mark_all_read(user_id: str) -> bool:
    db = get_db()
    try:
        db.notifications.update_many({"user_id": user_id}, {"$set": {"is_read": True}})
        return True
    except Exception:
        return False


def delete_notification(notification_id: str) -> bool:
    db = get_db()
    try:
        db.notifications.delete_one({"_id": notification_id})
        return True
    except Exception:
        return False


# ═══════════════════════════════════════════════════════════════
#  UI COMPONENTS
# ═══════════════════════════════════════════════════════════════

_TYPE_ICONS = {
    "info":    "ℹ️",
    "success": "✅",
    "warning": "⚠️",
    "error":   "❌",
}


def render_notifications_page(user_id: str) -> None:
    """Full notifications page for any role."""
    from utils.styling import section_header, empty_state, divider

    section_header("🔔 Notifications", "Your latest updates and alerts")

    col1, col2 = st.columns([6, 1])
    with col2:
        if st.button("Mark all read", key="mark_all_read"):
            mark_all_read(user_id)
            st.rerun()

    notifications = get_user_notifications(user_id)

    if not notifications:
        empty_state("No notifications yet 🔕")
        return

    for notif in notifications:
        icon = _TYPE_ICONS.get(notif.get("type", "info"), "ℹ️")
        is_unread = not notif.get("is_read", False)
        unread_style = "border-left: 4px solid #889FC4;" if is_unread else "border-left: 4px solid #ccc;"

        st.markdown(
            f"""
            <div class='es-notif-item {"unread" if is_unread else ""}' style='{unread_style}'>
                <div class='es-notif-title'>{icon} {notif['title']}</div>
                <div class='es-notif-msg'>{notif['message']}</div>
                <div class='es-notif-time'>{format_datetime(notif.get('created_at'))}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        col_a, col_b, _ = st.columns([1, 1, 5])
        with col_a:
            if is_unread and st.button("Mark read", key=f"read_{notif['id']}"):
                mark_as_read(notif["id"])
                st.rerun()
        with col_b:
            if st.button("🗑️", key=f"del_notif_{notif['id']}"):
                delete_notification(notif["id"])
                st.rerun()


def render_admin_broadcast_form(all_user_ids: list[str]) -> None:
    """Admin form to broadcast a notification to all users."""
    with st.form("broadcast_form"):
        st.subheader("📢 Broadcast Announcement")
        title = st.text_input("Title *")
        message = st.text_area("Message *", height=80)
        notif_type = st.selectbox("Type", ["info", "success", "warning", "error"])
        submitted = st.form_submit_button("Broadcast to All Users", use_container_width=True)

    if submitted:
        if not title or not message:
            st.error("Title and message are required.")
            return
        count = broadcast_notification(all_user_ids, title, message, notif_type)
        st.success(f"Sent to {count} user(s)! 📣")
