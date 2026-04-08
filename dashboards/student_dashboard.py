"""
dashboards/student_dashboard.py
--------------------------------
Student-facing dashboard: browse events, registrations, clubs,
notifications, certificates, recommendations, and payments.
"""

from __future__ import annotations

import streamlit as st

from modules.events import (
    get_all_events,
    get_user_registrations,
    register_for_event,
    cancel_registration,
    is_registration_open,
)
from modules.clubs import get_all_clubs
from modules.notifications import get_unread_count, render_notifications_page
from modules.certificates import get_user_certificates, render_certificate_card
from modules.payments import get_user_payments, render_payment_widget
from modules.recommendations import render_recommendations
from utils.helpers import format_date, format_currency, status_badge, is_event_upcoming
from utils.styling import (
    section_header, card_container, metric_card,
    event_card, empty_state, divider, notification_badge,
)


def render_student_sidebar() -> str:
    """Render sidebar navigation. Returns the selected page name."""
    user_name = st.session_state.get("user_name", "Student")
    user_id = st.session_state.get("user_id", "")
    unread = get_unread_count(user_id)

    st.sidebar.markdown(
        f"""
        <div class='es-brand'>
            <div>
                <div class='es-brand-name'>🎓 EventSphere</div>
                <div class='es-brand-tagline'>STUDENT PORTAL</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.sidebar.markdown(f"**{user_name}**")
    st.sidebar.markdown("---")

    pages = [
        ("🏠 Dashboard",       "Dashboard"),
        ("🎪 Browse Events",   "Events"),
        ("🏛️ Clubs",           "Clubs"),
        (f"🔔 Notifications{notification_badge(unread)}", "Notifications"),
        ("📅 My Registrations","Registrations"),
        ("💳 Payments",        "Payments"),
        ("📜 Certificates",    "Certificates"),
    ]

    selected = st.session_state.get("student_page", "Dashboard")

    for label, page in pages:
        if st.sidebar.button(label, key=f"nav_{page}", use_container_width=True):
            st.session_state["student_page"] = page
            selected = page

    st.sidebar.markdown("---")
    if st.sidebar.button("🚪 Logout", use_container_width=True):
        from auth.login import logout_user
        logout_user()
        st.rerun()

    return selected


def render_overview(user_id: str) -> None:
    """Student dashboard home overview."""
    registrations = get_user_registrations(user_id)
    upcoming = [r for r in registrations if r.get("events") and is_event_upcoming(r["events"]["event_date"])]
    payments = get_user_payments(user_id)
    paid_count = sum(1 for p in payments if p["status"] == "paid")

    # ── Stats row ──────────────────────────────────────────────
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        metric_card("Events Registered", str(len(registrations)), "🎟️")
    with c2:
        metric_card("Upcoming Events", str(len(upcoming)), "📅")
    with c3:
        metric_card("Payments Made", str(paid_count), "💳")
    with c4:
        from modules.certificates import get_user_certificates
        certs = get_user_certificates(user_id)
        metric_card("Certificates", str(len(certs)), "📜")

    divider()

    # ── Recommendations ───────────────────────────────────────
    render_recommendations(user_id)

    divider()

    # ── Upcoming registered events ────────────────────────────
    section_header("📅 Your Upcoming Events")
    if not upcoming:
        empty_state("No upcoming events. Browse and register for some! 🎪")
    else:
        for reg in upcoming[:4]:
            evt = reg["events"]
            with card_container(evt["id"]):
                col1, col2 = st.columns([5, 1])
                with col1:
                    st.markdown(f"**{evt['title']}**")
                    st.caption(f"📅 {format_date(evt['event_date'])}  |  📍 {evt.get('venue') or 'TBA'}")
                with col2:
                    if st.button("Cancel", key=f"cancel_{reg['id']}", type="secondary"):
                        if cancel_registration(evt["id"], user_id):
                            st.success("Registration cancelled.")
                            st.rerun()


def render_browse_events(user_id: str) -> None:
    """Browse and register for approved events."""
    from config import EVENT_CATEGORIES

    section_header("🎪 Browse Events", "Discover what's happening on campus")

    # ── Filters ────────────────────────────────────────────────
    col1, col2, col3 = st.columns(3)
    with col1:
        search = st.text_input("🔍 Search", placeholder="Event name…")
    with col2:
        cat_filter = st.selectbox("Category", ["All"] + EVENT_CATEGORIES)
    with col3:
        price_filter = st.selectbox("Price", ["All", "Free", "Paid"])

    events = get_all_events(status="approved")

    # ── Apply filters ──────────────────────────────────────────
    if search:
        events = [e for e in events if search.lower() in e["title"].lower()]
    if cat_filter != "All":
        events = [e for e in events if e["category"] == cat_filter]
    if price_filter == "Free":
        events = [e for e in events if not e.get("is_paid")]
    if price_filter == "Paid":
        events = [e for e in events if e.get("is_paid")]

    upcoming = [e for e in events if is_event_upcoming(e["event_date"])]
    past = [e for e in events if not is_event_upcoming(e["event_date"])]

    st.caption(f"Showing {len(events)} event(s)")
    divider()

    if not upcoming:
        empty_state("No upcoming events match your filters.")
    else:
        cols = st.columns(2)
        for i, event in enumerate(upcoming):
            with cols[i % 2]:
                with card_container(event["id"]):
                    cat_colour = "#A6BEE0"
                    st.markdown(
                        f"<span style='background:{cat_colour};color:#2C3E6B;"
                        f"padding:2px 10px;border-radius:12px;font-size:0.73rem;"
                        f"font-weight:700;'>{event.get('category','')}</span>",
                        unsafe_allow_html=True,
                    )
                    st.markdown(f"### {event['title']}")
                    st.caption(
                        f"📅 {format_date(event['event_date'])}  |  "
                        f"📍 {event.get('venue') or 'TBA'}  |  "
                        f"{'💰 ' + format_currency(event.get('ticket_price',0)) if event.get('is_paid') else '🆓 Free'}"
                    )
                    if event.get("description"):
                        st.write(event["description"][:200] + ("…" if len(event.get("description","")) > 200 else ""))

                    registered = is_registered(event["id"], user_id)
                    open_reg = is_registration_open(event)

                    if registered:
                        st.success("✓ You are registered")
                        if st.button("Cancel Registration", key=f"cancel_e_{event['id']}"):
                            cancel_registration(event["id"], user_id)
                            st.success("Cancelled.")
                            st.rerun()
                    elif open_reg:
                        if st.button("Register Now →", key=f"reg_{event['id']}", type="primary"):
                            result = register_for_event(event["id"], user_id)
                            if result:
                                st.success("Registered! 🎉")
                                st.rerun()
                    else:
                        st.warning("Registration closed")

    if past:
        with st.expander(f"📂 Past Events ({len(past)})"):
            for event in past[:10]:
                st.markdown(f"- **{event['title']}** — {format_date(event['event_date'])}")


def render_my_registrations(user_id: str) -> None:
    """Show all of the student's registrations."""
    section_header("📅 My Registrations")
    registrations = get_user_registrations(user_id)

    if not registrations:
        empty_state("You haven't registered for any events yet.")
        return

    for reg in registrations:
        evt = reg.get("events") or {}
        with card_container(reg["id"]):
            col1, col2 = st.columns([5, 2])
            with col1:
                st.markdown(f"**{evt.get('title','Unknown')}**")
                st.caption(
                    f"📅 {format_date(evt.get('event_date'))}  |  "
                    f"📍 {evt.get('venue') or 'TBA'}  |  "
                    f"Category: {evt.get('category','')}"
                )
                st.caption(f"Registered on: {format_date(reg.get('registered_at'))}")
            with col2:
                if evt.get("is_paid"):
                    from modules.payments import get_payment_for_registration
                    payment = get_payment_for_registration(reg["id"])
                    if payment:
                        pstatus = payment["status"]
                        st.markdown(
                            f"Payment: {status_badge(pstatus)}",
                            unsafe_allow_html=True,
                        )
                        if pstatus == "pending":
                            render_payment_widget(reg, evt)
                else:
                    st.success("🆓 Free Event")


def render_my_payments(user_id: str) -> None:
    """Payment history tab."""
    section_header("💳 Payment History")
    payments = get_user_payments(user_id)

    if not payments:
        empty_state("No payment records yet.")
        return

    total_paid = sum(p["amount"] for p in payments if p["status"] == "paid")
    st.info(f"💰 Total paid: **{format_currency(total_paid)}**")
    divider()

    for p in payments:
        evt = p.get("events") or {}
        with card_container(p["id"]):
            col1, col2, col3 = st.columns([4, 2, 1])
            with col1:
                st.markdown(f"**{evt.get('title','—')}**")
                st.caption(f"Ref: `{p.get('transaction_ref','—')}`")
            with col2:
                st.markdown(f"{format_currency(p['amount'])}")
                st.caption(format_date(p.get("created_at")))
            with col3:
                st.markdown(status_badge(p["status"]), unsafe_allow_html=True)


def render_my_certificates(user_id: str) -> None:
    """Certificates tab."""
    from modules.certificates import get_user_certificates

    section_header("📜 My Certificates")
    certs = get_user_certificates(user_id)

    if not certs:
        empty_state("No certificates yet. Participate in events to earn them!")
        return

    for cert in certs:
        render_certificate_card(cert)


def render_student_dashboard() -> None:
    """Main entry point for the student dashboard."""
    user_id = st.session_state.get("user_id", "")
    page = render_student_sidebar()

    if page == "Dashboard":
        render_overview(user_id)
    elif page == "Events":
        render_browse_events(user_id)
    elif page == "Clubs":
        _render_clubs_page(user_id)
    elif page == "Notifications":
        render_notifications_page(user_id)
    elif page == "Registrations":
        render_my_registrations(user_id)
    elif page == "Payments":
        render_my_payments(user_id)
    elif page == "Certificates":
        render_my_certificates(user_id)


def _render_clubs_page(user_id: str) -> None:
    """Browse and join clubs."""
    from modules.clubs import render_club_card

    section_header("🏛️ Clubs", "Join clubs to stay in the loop")
    clubs = get_all_clubs(status="approved")

    if not clubs:
        empty_state("No clubs available yet.")
        return

    for club in clubs:
        render_club_card(club, user_id=user_id, user_role="student")
