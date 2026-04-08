"""
dashboards/coordinator_dashboard.py
-------------------------------------
Club Coordinator dashboard: manage events, clubs, members,
view participants, issue certificates, and notifications.
"""

from __future__ import annotations

import streamlit as st

from modules.events import (
    get_events_by_coordinator,
    get_participants,
    delete_event,
    render_event_form,
)
from modules.clubs import (
    get_clubs_by_coordinator,
    get_members,
    get_pending_members,
    approve_member,
    reject_member,
    remove_member,
    render_create_club_form,
)
from modules.notifications import get_unread_count, render_notifications_page
from modules.certificates import render_issue_certificate_form
from utils.helpers import format_date, status_badge
from utils.styling import (
    section_header, card_container, metric_card,
    empty_state, divider, notification_badge,
)


def render_coordinator_sidebar() -> str:
    """Sidebar for coordinator. Returns selected page."""
    user_name = st.session_state.get("user_name", "Coordinator")
    user_id = st.session_state.get("user_id", "")
    unread = get_unread_count(user_id)

    st.sidebar.markdown(
        f"""
        <div class='es-brand'>
            <div>
                <div class='es-brand-name'>🎯 EventSphere</div>
                <div class='es-brand-tagline'>COORDINATOR PORTAL</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.sidebar.markdown(f"**{user_name}**")
    st.sidebar.markdown("---")

    pages = [
        ("🏠 Dashboard",          "Dashboard"),
        ("➕ Create Event",        "CreateEvent"),
        ("📋 My Events",           "MyEvents"),
        ("🏛️ My Clubs",            "MyClubs"),
        ("➕ Create Club",         "CreateClub"),
        (f"🔔 Notifications{notification_badge(unread)}", "Notifications"),
        ("📜 Issue Certificates",  "Certificates"),
    ]

    selected = st.session_state.get("coord_page", "Dashboard")
    for label, page in pages:
        if st.sidebar.button(label, key=f"coord_nav_{page}", use_container_width=True):
            st.session_state["coord_page"] = page
            selected = page

    st.sidebar.markdown("---")
    if st.sidebar.button("🚪 Logout", use_container_width=True):
        from auth.login import logout_user
        logout_user()
        st.rerun()

    return selected


def render_coordinator_overview(user_id: str) -> None:
    """Coordinator home overview with stats."""
    events = get_events_by_coordinator(user_id)
    clubs  = get_clubs_by_coordinator(user_id)

    approved_events = [e for e in events if e["status"] == "approved"]
    pending_events  = [e for e in events if e["status"] == "pending"]
    total_participants = 0
    for evt in approved_events:
        total_participants += len(get_participants(evt["id"]))

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        metric_card("Total Events", str(len(events)), "📋")
    with c2:
        metric_card("Approved", str(len(approved_events)), "✅")
    with c3:
        metric_card("Pending Approval", str(len(pending_events)), "⏳")
    with c4:
        metric_card("Total Participants", str(total_participants), "👥")

    divider()

    # ── Recent events quick view ───────────────────────────────
    section_header("📋 Recent Events")
    if not events:
        empty_state("No events yet. Create your first event!")
    else:
        for evt in events[:5]:
            with card_container(evt["id"]):
                col1, col2, col3 = st.columns([5, 2, 1])
                with col1:
                    st.markdown(f"**{evt['title']}**")
                    st.caption(f"📅 {format_date(evt['event_date'])}  |  {evt.get('category','')}")
                with col2:
                    st.markdown(status_badge(evt["status"]), unsafe_allow_html=True)
                with col3:
                    parts = len(get_participants(evt["id"]))
                    st.caption(f"👥 {parts}")

    divider()

    # ── Clubs quick view ───────────────────────────────────────
    section_header("🏛️ My Clubs")
    if not clubs:
        empty_state("No clubs yet. Create one!")
    else:
        for club in clubs:
            col1, col2 = st.columns([5, 2])
            with col1:
                st.markdown(f"**{club['name']}** — {club.get('category','')}")
            with col2:
                st.markdown(status_badge(club["status"]), unsafe_allow_html=True)


def render_my_events(user_id: str) -> None:
    """Manage all events created by this coordinator."""
    section_header("📋 My Events", "View, edit and manage your events")

    events = get_events_by_coordinator(user_id)
    if not events:
        empty_state("No events created yet. Use 'Create Event' to get started.")
        return

    # Status filter
    status_filter = st.selectbox("Filter by Status", ["All", "pending", "approved", "rejected"])
    if status_filter != "All":
        events = [e for e in events if e["status"] == status_filter]

    for evt in events:
        with card_container(evt["id"]):
            col1, col2 = st.columns([6, 2])
            with col1:
                st.markdown(f"### {evt['title']}")
                st.caption(
                    f"📅 {format_date(evt['event_date'])}  |  "
                    f"📍 {evt.get('venue') or 'TBA'}  |  "
                    f"Category: {evt['category']}"
                )
                st.markdown(status_badge(evt["status"]), unsafe_allow_html=True)
            with col2:
                participants = get_participants(evt["id"])
                st.metric("Participants", len(participants))

            # Expandable participants list
            if participants:
                with st.expander(f"👥 View {len(participants)} Participant(s)"):
                    for p in participants:
                        user = p.get("users") or {}
                        st.markdown(
                            f"- **{user.get('full_name','—')}** "
                            f"({user.get('email','')}) — "
                            f"{user.get('department','')}"
                        )

            # Edit / Delete controls (only if pending or approved)
            col_edit, col_del, _ = st.columns([1, 1, 4])
            with col_edit:
                if st.button("✏️ Edit", key=f"edit_evt_{evt['id']}"):
                    st.session_state[f"editing_event"] = evt["id"]
                    st.rerun()
            with col_del:
                if st.button("🗑️ Delete", key=f"del_evt_{evt['id']}"):
                    if delete_event(evt["id"]):
                        st.success("Event deleted.")
                        st.rerun()

    # ── Edit form (shown when an event is selected for editing) ─
    editing_id = st.session_state.get("editing_event")
    if editing_id:
        from modules.events import get_event_by_id
        existing = get_event_by_id(editing_id)
        if existing and existing.get("coordinator_id") == user_id:
            divider()
            st.subheader("✏️ Edit Event")
            render_event_form(user_id, existing=existing)
            if st.button("Close Editor"):
                del st.session_state["editing_event"]
                st.rerun()


def render_my_clubs(user_id: str) -> None:
    """View and manage clubs owned by this coordinator."""
    section_header("🏛️ My Clubs", "Manage members and club details")

    clubs = get_clubs_by_coordinator(user_id)
    if not clubs:
        empty_state("No clubs yet. Create one in 'Create Club'.")
        return

    for club in clubs:
        with card_container(club["id"]):
            st.markdown(f"### {club['name']}")
            col1, col2 = st.columns([4, 2])
            with col1:
                st.caption(f"Category: {club.get('category','—')}  |  Status: {club['status'].capitalize()}")
                st.write(club.get("description", ""))
            with col2:
                st.markdown(status_badge(club["status"]), unsafe_allow_html=True)

            if club["status"] == "approved":
                # Pending membership requests
                pending = get_pending_members(club["id"])
                if pending:
                    st.markdown(f"**⏳ Pending Applications ({len(pending)})**")
                    for mem in pending:
                        user = mem.get("users") or {}
                        c1, c2, c3 = st.columns([4, 1, 1])
                        with c1:
                            st.markdown(f"{user.get('full_name','—')} — {user.get('department','')}")
                        with c2:
                            if st.button("✅", key=f"approve_mem_{mem['id']}"):
                                approve_member(mem["id"])
                                st.rerun()
                        with c3:
                            if st.button("❌", key=f"reject_mem_{mem['id']}"):
                                reject_member(mem["id"])
                                st.rerun()

                # Current members
                members = get_members(club["id"])
                if members:
                    with st.expander(f"👥 Current Members ({len(members)})"):
                        for mem in members:
                            user = mem.get("users") or {}
                            c1, c2 = st.columns([5, 1])
                            with c1:
                                st.markdown(
                                    f"- **{user.get('full_name','—')}** "
                                    f"({user.get('email','')})"
                                )
                            with c2:
                                if st.button("Remove", key=f"rm_mem_{mem['id']}"):
                                    remove_member(club["id"], mem.get("user_id",""))
                                    st.rerun()


def render_coordinator_certificates(user_id: str) -> None:
    """Issue certificates for events managed by this coordinator."""
    section_header("📜 Issue Certificates")

    events = get_events_by_coordinator(user_id)
    approved = [e for e in events if e["status"] == "approved"]

    if not approved:
        empty_state("No approved events. Certificates can only be issued for approved events.")
        return

    event_map = {e["title"]: e["id"] for e in approved}
    selected_title = st.selectbox("Select Event", list(event_map.keys()))
    selected_id = event_map[selected_title]

    render_issue_certificate_form(event_id=selected_id, admin_id=user_id)


def render_coordinator_dashboard() -> None:
    """Main entry point for coordinator dashboard."""
    user_id = st.session_state.get("user_id", "")
    page = render_coordinator_sidebar()

    if page == "Dashboard":
        render_coordinator_overview(user_id)
    elif page == "CreateEvent":
        section_header("➕ Create New Event")
        render_event_form(user_id)
    elif page == "MyEvents":
        render_my_events(user_id)
    elif page == "MyClubs":
        render_my_clubs(user_id)
    elif page == "CreateClub":
        section_header("➕ Create New Club")
        render_create_club_form(user_id)
    elif page == "Notifications":
        render_notifications_page(user_id)
    elif page == "Certificates":
        render_coordinator_certificates(user_id)
