"""
dashboards/admin_dashboard.py
------------------------------
Admin dashboard: approve/reject events & clubs, manage users,
monitor transactions, issue certificates, broadcast notifications,
and view system-wide statistics.
"""

from __future__ import annotations

import streamlit as st
import pandas as pd

from modules.events import get_all_events, approve_event, reject_event, delete_event
from modules.clubs import get_all_clubs, approve_club, reject_club
from modules.notifications import (
    get_unread_count,
    render_notifications_page,
    render_admin_broadcast_form,
)
from modules.payments import get_all_transactions, get_payment_stats
from modules.certificates import get_all_certificates, render_issue_certificate_form
from utils.helpers import format_date, format_datetime, format_currency, status_badge
from utils.styling import (
    section_header, card_container, metric_card,
    empty_state, divider, notification_badge,
)
from database.mongo_client import get_db


# ═══════════════════════════════════════════════════════════════
#  USER MANAGEMENT HELPERS
# ═══════════════════════════════════════════════════════════════

def get_all_users() -> list[dict]:
    db = get_db()
    try:
        raw = list(db.users.find().sort("created_at", -1))
        return [{**u, "id": u["_id"]} for u in raw]
    except Exception as exc:
        st.error(f"Failed to load users: {exc}")
        return []


def update_user_role(user_id: str, new_role: str) -> bool:
    db = get_db()
    try:
        db.users.update_one({"_id": user_id}, {"$set": {"role": new_role}})
        return True
    except Exception as exc:
        st.error(f"Role update failed: {exc}")
        return False


def delete_user(user_id: str) -> bool:
    db = get_db()
    try:
        db.users.delete_one({"_id": user_id})
        return True
    except Exception as exc:
        st.error(f"User deletion failed: {exc}")
        return False


# ═══════════════════════════════════════════════════════════════
#  SIDEBAR
# ═══════════════════════════════════════════════════════════════

def render_admin_sidebar() -> str:
    user_name = st.session_state.get("user_name", "Admin")
    user_id   = st.session_state.get("user_id", "")
    unread    = get_unread_count(user_id)

    st.sidebar.markdown(
        f"""
        <div class='es-brand'>
            <div>
                <div class='es-brand-name'>EventSphere</div>
                <div class='es-brand-tagline'>ADMIN CONTROL PANEL</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.sidebar.markdown(f"**{user_name}**")
    st.sidebar.markdown("---")

    pages = [
        ("Dashboard",            "Dashboard"),
        ("Event Approvals",       "EventApprovals"),
        ("Club Approvals",        "ClubApprovals"),
        ("User Management",       "Users"),
        ("Transactions",          "Transactions"),
        ("Certificates",          "Certificates"),
        (f"Notifications{notification_badge(unread)}", "Notifications"),
        ("Broadcast",             "Broadcast"),
    ]

    selected = st.session_state.get("admin_page", "Dashboard")
    for label, page in pages:
        if st.sidebar.button(label, key=f"admin_nav_{page}", use_container_width=True):
            st.session_state["admin_page"] = page
            selected = page

    st.sidebar.markdown("---")
    if st.sidebar.button("Logout", use_container_width=True):
        from auth.login import logout_user
        logout_user()
        st.rerun()

    return selected


# ═══════════════════════════════════════════════════════════════
#  OVERVIEW / STATS
# ═══════════════════════════════════════════════════════════════

def render_admin_overview() -> None:
    section_header("System Overview", "Platform-wide statistics at a glance")

    users   = get_all_users()
    events  = get_all_events()
    clubs   = get_all_clubs()
    pay_stats = get_payment_stats()

    students     = [u for u in users if u["role"] == "student"]
    coordinators = [u for u in users if u["role"] == "coordinator"]
    pending_ev   = [e for e in events if e["status"] == "pending"]
    pending_cl   = [c for c in clubs  if c["status"] == "pending"]

    # ── Row 1: user stats ──────────────────────────────────────
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        metric_card("Total Users",    str(len(users)),       "👥")
    with c2:
        metric_card("Students",       str(len(students)),    "🎓")
    with c3:
        metric_card("Coordinators",   str(len(coordinators)),"🎯")
    with c4:
        metric_card("Total Events",   str(len(events)),      "🎪")

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Row 2: operational stats ───────────────────────────────
    c5, c6, c7, c8 = st.columns(4)
    with c5:
        metric_card("Pending Events",  str(len(pending_ev)),  "⏳")
    with c6:
        metric_card("Approved Clubs",  str(len([c for c in clubs if c["status"]=="approved"])), "🏛️")
    with c7:
        metric_card("Pending Clubs",   str(len(pending_cl)),  "⌛")
    with c8:
        metric_card("Revenue Collected", format_currency(pay_stats["total_collected"]), "💰")

    divider()

    # ── Charts ─────────────────────────────────────────────────
    col_l, col_r = st.columns(2)

    with col_l:
        st.subheader("Events by Status")
        status_counts = {"Pending": len(pending_ev),
                         "Approved": len([e for e in events if e["status"]=="approved"]),
                         "Rejected": len([e for e in events if e["status"]=="rejected"])}
        try:
            import plotly.graph_objects as go
            fig = go.Figure(data=[go.Pie(
                labels=list(status_counts.keys()),
                values=list(status_counts.values()),
                hole=0.4,
                marker_colors=["#FFA500", "#2E7D32", "#C62828"],
            )])
            fig.update_layout(
                margin=dict(t=10, b=10, l=10, r=10),
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                height=260,
                showlegend=True,
            )
            st.plotly_chart(fig, use_container_width=True)
        except ImportError:
            for k, v in status_counts.items():
                st.write(f"{k}: {v}")

    with col_r:
        st.subheader("Payment Summary")
        try:
            import plotly.graph_objects as go
            pay_labels = ["Paid", "Pending", "Failed"]
            pay_values = [pay_stats["paid"], pay_stats["pending"], pay_stats["failed"]]
            fig2 = go.Figure(data=[go.Bar(
                x=pay_labels,
                y=pay_values,
                marker_color=["#2E7D32", "#FFA500", "#C62828"],
            )])
            fig2.update_layout(
                margin=dict(t=10, b=10, l=10, r=10),
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                height=260,
                showlegend=False,
            )
            st.plotly_chart(fig2, use_container_width=True)
        except ImportError:
            for k, v in zip(pay_labels, pay_values):
                st.write(f"{k}: {v}")

    divider()

    # ── Pending approvals quick list ───────────────────────────
    if pending_ev:
        section_header(f"Events Awaiting Approval ({len(pending_ev)})")
        for evt in pending_ev[:3]:
            col1, col2, col3 = st.columns([5, 1, 1])
            with col1:
                st.markdown(f"**{evt['title']}** — {evt['category']} — {format_date(evt['event_date'])}")
            with col2:
                if st.button("✅", key=f"ov_approve_ev_{evt['id']}"):
                    approve_event(evt["id"])
                    _notify_event_decision(evt, approved=True)
                    st.rerun()
            with col3:
                if st.button("❌", key=f"ov_reject_ev_{evt['id']}"):
                    reject_event(evt["id"])
                    _notify_event_decision(evt, approved=False)
                    st.rerun()


# ═══════════════════════════════════════════════════════════════
#  EVENT APPROVALS
# ═══════════════════════════════════════════════════════════════

def _notify_event_decision(event: dict, approved: bool) -> None:
    """Send a notification to the coordinator about the event decision."""
    from modules.notifications import send_notification
    action = "approved" if approved else "rejected"
    notif_type = "success" if approved else "warning"
    send_notification(
        user_id=event["coordinator_id"],
        title=f"Event {action.capitalize()} 📋",
        message=f"Your event '{event['title']}' has been {action} by the admin.",
        notif_type=notif_type,
        related_event_id=event["id"],
    )


def render_event_approvals() -> None:
    section_header("Event Approvals", "Review and approve or reject coordinator-submitted events")

    tab_pending, tab_all = st.tabs(["Pending", "All Events"])

    with tab_pending:
        pending = get_all_events(status="pending")
        if not pending:
            empty_state("No events pending approval.")
        else:
            for evt in pending:
                with card_container(evt["id"]):
                    col1, col2 = st.columns([6, 2])
                    with col1:
                        st.markdown(f"### {evt['title']}")
                        st.caption(
                            f"Category: {evt['category']}  |  "
                            f"Date: {format_date(evt['event_date'])}  |  "
                            f"Venue: {evt.get('venue') or 'TBA'}"
                        )
                        if evt.get("description"):
                            st.write(evt["description"][:200])
                        price_info = (
                            f"Paid — {format_currency(evt.get('ticket_price',0))}"
                            if evt.get("is_paid") else "Free"
                        )
                        st.caption(price_info)
                    with col2:
                        if st.button("Approve", key=f"appr_ev_{evt['id']}", type="primary"):
                            approve_event(evt["id"])
                            _notify_event_decision(evt, approved=True)
                            st.success("Event approved!")
                            st.rerun()
                        if st.button("Reject", key=f"rej_ev_{evt['id']}"):
                            reject_event(evt["id"])
                            _notify_event_decision(evt, approved=False)
                            st.warning("Event rejected.")
                            st.rerun()

    with tab_all:
        status_f = st.selectbox("Filter", ["All", "approved", "pending", "rejected"], key="ev_status_f")
        all_events = get_all_events(status=None if status_f == "All" else status_f)
        if not all_events:
            empty_state("No events found.")
        else:
            df = pd.DataFrame([{
                "Title":    e["title"],
                "Category": e["category"],
                "Date":     format_date(e["event_date"]),
                "Status":   e["status"].capitalize(),
                "Paid":     "Yes" if e.get("is_paid") else "No",
            } for e in all_events])
            st.dataframe(df, use_container_width=True, hide_index=True)

            # Delete
            del_title = st.selectbox("Select event to delete", ["—"] + [e["title"] for e in all_events], key="del_ev_sel")
            if del_title != "—":
                target = next((e for e in all_events if e["title"] == del_title), None)
                if target and st.button("Delete Selected Event", type="secondary"):
                    delete_event(target["id"])
                    st.success("Deleted.")
                    st.rerun()


# ═══════════════════════════════════════════════════════════════
#  CLUB APPROVALS
# ═══════════════════════════════════════════════════════════════

def render_club_approvals() -> None:
    section_header("Club Approvals", "Review and approve or reject new clubs")

    tab_pending, tab_all = st.tabs(["Pending", "All Clubs"])

    with tab_pending:
        pending = get_all_clubs(status="pending")
        if not pending:
            empty_state("No clubs pending approval.")
        else:
            for club in pending:
                with card_container(club["id"]):
                    col1, col2 = st.columns([6, 2])
                    with col1:
                        st.markdown(f"### {club['name']}")
                        coordinator = (club.get("users") or {})
                        st.caption(
                            f"Category: {club.get('category','—')}  |  "
                            f"Coordinator: {coordinator.get('full_name','—')}"
                        )
                        st.write(club.get("description", ""))
                    with col2:
                        if st.button("Approve", key=f"appr_cl_{club['id']}", type="primary"):
                            approve_club(club["id"])
                            _notify_club_decision(club, approved=True)
                            st.success("Club approved!")
                            st.rerun()
                        if st.button("Reject", key=f"rej_cl_{club['id']}"):
                            reject_club(club["id"])
                            _notify_club_decision(club, approved=False)
                            st.warning("Club rejected.")
                            st.rerun()

    with tab_all:
        all_clubs = get_all_clubs()
        if not all_clubs:
            empty_state("No clubs in system.")
        else:
            df = pd.DataFrame([{
                "Name":     c["name"],
                "Category": c.get("category", "—"),
                "Status":   c["status"].capitalize(),
            } for c in all_clubs])
            st.dataframe(df, use_container_width=True, hide_index=True)


def _notify_club_decision(club: dict, approved: bool) -> None:
    from modules.notifications import send_notification
    if not club.get("coordinator_id"):
        return
    action = "approved" if approved else "rejected"
    send_notification(
        user_id=club["coordinator_id"],
        title=f"Club {action.capitalize()}",
        message=f"Your club '{club['name']}' has been {action} by the admin.",
        notif_type="success" if approved else "warning",
    )


# ═══════════════════════════════════════════════════════════════
#  USER MANAGEMENT
# ═══════════════════════════════════════════════════════════════

def render_user_management() -> None:
    section_header("User Management", "View, update roles, and remove users")

    users = get_all_users()
    if not users:
        empty_state("No users in the system.")
        return

    # ── Search ─────────────────────────────────────────────────
    search = st.text_input("Search by name or email")
    role_filter = st.selectbox("Filter by Role", ["All", "student", "coordinator", "admin"])

    filtered = users
    if search:
        filtered = [u for u in filtered if
                    search.lower() in u.get("full_name","").lower() or
                    search.lower() in u.get("email","").lower()]
    if role_filter != "All":
        filtered = [u for u in filtered if u["role"] == role_filter]

    st.caption(f"Showing {len(filtered)} user(s)")
    divider()

    for u in filtered:
        with card_container(u["id"]):
            col1, col2, col3 = st.columns([4, 2, 1])
            with col1:
                st.markdown(f"**{u['full_name']}**")
                st.caption(f"{u['email']}  |  {u.get('department','—')}")
            with col2:
                new_role = st.selectbox(
                    "Role",
                    ["student", "coordinator", "admin"],
                    index=["student","coordinator","admin"].index(u["role"]),
                    key=f"role_sel_{u['id']}",
                )
                if new_role != u["role"]:
                    if st.button("Save Role", key=f"save_role_{u['id']}"):
                        if update_user_role(u["id"], new_role):
                            st.success("Role updated.")
                            st.rerun()
            with col3:
                current_admin_id = st.session_state.get("user_id", "")
                if u["id"] != current_admin_id:
                    if st.button("🗑️", key=f"del_user_{u['id']}", help="Delete user"):
                        delete_user(u["id"])
                        st.rerun()


# ═══════════════════════════════════════════════════════════════
#  TRANSACTIONS
# ═══════════════════════════════════════════════════════════════

def render_transactions() -> None:
    section_header("Transaction Monitor", "Full payment history across all events")

    stats = get_payment_stats()
    c1, c2, c3, c4 = st.columns(4)
    with c1: metric_card("Total Transactions", str(stats["total"]))
    with c2: metric_card("Paid",    str(stats["paid"]))
    with c3: metric_card("Pending", str(stats["pending"]))
    with c4: metric_card("Revenue", format_currency(stats["total_collected"]))

    divider()

    transactions = get_all_transactions()
    if not transactions:
        empty_state("No transactions yet.")
        return

    # Status filter
    status_f = st.selectbox("Filter", ["All", "paid", "pending", "failed"], key="txn_filter")
    if status_f != "All":
        transactions = [t for t in transactions if t["status"] == status_f]

    rows = []
    for t in transactions:
        user  = t.get("users") or {}
        event = t.get("events") or {}
        rows.append({
            "Ref":    t.get("transaction_ref", "—"),
            "User":   user.get("full_name", "—"),
            "Event":  event.get("title", "—"),
            "Amount": format_currency(t["amount"]),
            "Status": t["status"].capitalize(),
            "Date":   format_date(t.get("created_at")),
        })

    df = pd.DataFrame(rows)
    st.dataframe(df, use_container_width=True, hide_index=True)


# ═══════════════════════════════════════════════════════════════
#  CERTIFICATES
# ═══════════════════════════════════════════════════════════════

def render_admin_certificates() -> None:
    section_header("Certificate Management", "Issue certificates for approved events")

    tab_issue, tab_issued = st.tabs(["Issue Certificate", "All Issued"])

    with tab_issue:
        admin_id   = st.session_state.get("user_id", "")
        all_events = get_all_events(status="approved")
        if not all_events:
            empty_state("No approved events available.")
        else:
            event_map = {e["title"]: e["id"] for e in all_events}
            selected  = st.selectbox("Select Event", list(event_map.keys()))
            render_issue_certificate_form(event_map[selected], admin_id)

    with tab_issued:
        certs = get_all_certificates()
        if not certs:
            empty_state("No certificates issued yet.")
        else:
            rows = []
            for c in certs:
                user  = c.get("users") or {}
                event = c.get("events") or {}
                rows.append({
                    "Student": user.get("full_name","—"),
                    "Email":   user.get("email","—"),
                    "Event":   event.get("title","—"),
                    "Type":    c["cert_type"].capitalize(),
                    "Issued":  format_date(c.get("issued_at")),
                })
            df = pd.DataFrame(rows)
            st.dataframe(df, use_container_width=True, hide_index=True)


# ═══════════════════════════════════════════════════════════════
#  MAIN ENTRY
# ═══════════════════════════════════════════════════════════════

def render_admin_dashboard() -> None:
    """Main entry point for the admin dashboard."""
    user_id = st.session_state.get("user_id", "")
    page    = render_admin_sidebar()

    if page == "Dashboard":
        render_admin_overview()
    elif page == "EventApprovals":
        render_event_approvals()
    elif page == "ClubApprovals":
        render_club_approvals()
    elif page == "Users":
        render_user_management()
    elif page == "Transactions":
        render_transactions()
    elif page == "Certificates":
        render_admin_certificates()
    elif page == "Notifications":
        render_notifications_page(user_id)
    elif page == "Broadcast":
        users = get_all_users()
        all_ids = [u["id"] for u in users]
        render_admin_broadcast_form(all_ids)
