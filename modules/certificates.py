"""
modules/certificates.py
-----------------------
Certificate issuance and download — MongoDB version.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from io import BytesIO

import streamlit as st

from config import CERT_PARTICIPATION, CERT_WINNER, CERT_ORGANIZER
from database.mongo_client import get_db


# ═══════════════════════════════════════════════════════════════
#  DATABASE OPERATIONS
# ═══════════════════════════════════════════════════════════════

def issue_certificate(
    event_id: str,
    user_id: str,
    cert_type: str,
    issued_by: str,
    file_url: str = "",
) -> dict | None:
    """
    Upsert a certificate document in MongoDB.
    Uses (event_id, user_id, cert_type) as the unique composite key.
    """
    db = get_db()
    now = datetime.utcnow().isoformat()
    try:
        # Check if already exists
        existing = db.certificates.find_one(
            {"event_id": event_id, "user_id": user_id, "cert_type": cert_type}
        )
        if existing:
            db.certificates.update_one(
                {"_id": existing["_id"]},
                {"$set": {"file_url": file_url, "issued_by": issued_by, "issued_at": now}},
            )
            return {**existing, "id": existing["_id"]}

        doc = {
            "_id": str(uuid.uuid4()),
            "event_id": event_id,
            "user_id": user_id,
            "cert_type": cert_type,
            "file_url": file_url,
            "issued_by": issued_by,
            "issued_at": now,
        }
        db.certificates.insert_one(doc)
        return {**doc, "id": doc["_id"]}
    except Exception as exc:
        st.error(f"Certificate issuance failed: {exc}")
        return None


def get_user_certificates(user_id: str) -> list[dict]:
    """Return all certificates for a student, with event details."""
    db = get_db()
    try:
        raw = list(db.certificates.find({"user_id": user_id}).sort("issued_at", -1))
        result = []
        for cert in raw:
            event = db.events.find_one(
                {"_id": cert["event_id"]},
                {"title": 1, "event_date": 1, "category": 1},
            )
            result.append({
                **cert,
                "id": cert["_id"],
                "events": {**event, "id": event["_id"]} if event else None,
            })
        return result
    except Exception as exc:
        st.error(f"Failed to load certificates: {exc}")
        return []


def get_certificates_for_event(event_id: str) -> list[dict]:
    """Return all certificates issued for an event."""
    db = get_db()
    try:
        raw = list(db.certificates.find({"event_id": event_id}))
        result = []
        for cert in raw:
            user = db.users.find_one({"_id": cert["user_id"]}, {"full_name": 1, "email": 1})
            result.append({
                **cert,
                "id": cert["_id"],
                "users": {**user, "id": user["_id"]} if user else None,
            })
        return result
    except Exception:
        return []


def get_all_certificates() -> list[dict]:
    """Admin: fetch all certificates across events."""
    db = get_db()
    try:
        raw = list(db.certificates.find().sort("issued_at", -1))
        result = []
        for cert in raw:
            event = db.events.find_one({"_id": cert["event_id"]}, {"title": 1})
            user = db.users.find_one({"_id": cert["user_id"]}, {"full_name": 1, "email": 1})
            result.append({
                **cert,
                "id": cert["_id"],
                "events": {**event, "id": event["_id"]} if event else None,
                "users": {**user, "id": user["_id"]} if user else None,
            })
        return result
    except Exception:
        return []


# ═══════════════════════════════════════════════════════════════
#  PDF CERTIFICATE GENERATION (fpdf2)
# ═══════════════════════════════════════════════════════════════

def generate_certificate_pdf(
    student_name: str,
    event_title: str,
    event_date: str,
    cert_type: str,
    college_name: str = "EventSphere College",
) -> bytes:
    """
    Generate a simple PDF certificate using fpdf2.

    Returns
    -------
    bytes
        The raw PDF bytes ready for download.
    """
    try:
        from fpdf import FPDF
    except ImportError:
        return b""

    pdf = FPDF(orientation="L", unit="mm", format="A4")
    pdf.add_page()

    # ── Background gradient rectangle ─────────────────────────
    pdf.set_fill_color(232, 232, 227)   # #E8E8E3
    pdf.rect(0, 0, 297, 210, "F")

    # ── Decorative border ──────────────────────────────────────
    pdf.set_draw_color(136, 159, 196)   # #889FC4
    pdf.set_line_width(2)
    pdf.rect(10, 10, 277, 190)
    pdf.set_line_width(0.5)
    pdf.rect(13, 13, 271, 184)

    # ── College / Logo area ────────────────────────────────────
    pdf.set_font("Helvetica", "B", 14)
    pdf.set_text_color(44, 62, 107)     # #2C3E6B
    pdf.set_xy(0, 22)
    pdf.cell(297, 10, college_name.upper(), align="C")

    # ── Certificate heading ────────────────────────────────────
    pdf.set_font("Helvetica", "B", 28)
    pdf.set_text_color(44, 62, 107)
    pdf.set_xy(0, 40)
    pdf.cell(297, 18, "CERTIFICATE", align="C")

    cert_label = {
        CERT_PARTICIPATION: "of Participation",
        CERT_WINNER: "of Achievement",
        CERT_ORGANIZER: "of Appreciation",
    }.get(cert_type, "of Participation")

    pdf.set_font("Helvetica", "I", 16)
    pdf.set_text_color(126, 139, 177)   # #7E8BB1
    pdf.set_xy(0, 60)
    pdf.cell(297, 10, cert_label, align="C")

    # ── Body ───────────────────────────────────────────────────
    pdf.set_font("Helvetica", "", 12)
    pdf.set_text_color(80, 80, 80)
    pdf.set_xy(0, 82)
    pdf.cell(297, 8, "This is to certify that", align="C")

    # ── Recipient name ─────────────────────────────────────────
    pdf.set_font("Helvetica", "B", 22)
    pdf.set_text_color(44, 62, 107)
    pdf.set_xy(0, 95)
    pdf.cell(297, 14, student_name, align="C")

    # ── Event ──────────────────────────────────────────────────
    pdf.set_font("Helvetica", "", 12)
    pdf.set_text_color(80, 80, 80)
    pdf.set_xy(0, 116)
    pdf.cell(297, 8, "has successfully participated in", align="C")

    pdf.set_font("Helvetica", "B", 14)
    pdf.set_text_color(136, 159, 196)
    pdf.set_xy(0, 128)
    pdf.cell(297, 10, event_title, align="C")

    pdf.set_font("Helvetica", "", 11)
    pdf.set_text_color(120, 120, 120)
    pdf.set_xy(0, 143)
    pdf.cell(297, 8, f"held on {event_date}", align="C")

    # ── Signature line ─────────────────────────────────────────
    pdf.set_draw_color(136, 159, 196)
    pdf.set_line_width(0.5)
    pdf.line(80, 175, 160, 175)
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(100, 100, 100)
    pdf.set_xy(0, 177)
    pdf.cell(297, 6, "Authorised Signatory", align="C")

    return bytes(pdf.output())


# ═══════════════════════════════════════════════════════════════
#  UI COMPONENTS
# ═══════════════════════════════════════════════════════════════

def render_certificate_card(cert: dict) -> None:
    """Render a certificate card with download button."""
    from utils.helpers import format_date

    event = cert.get("events") or {}
    col1, col2 = st.columns([4, 1])
    with col1:
        st.markdown(
            f"**{event.get('title', 'Unknown Event')}**  \n"
            f"Type: `{cert['cert_type'].capitalize()}`  \n"
            f"Issued: {format_date(cert.get('issued_at'))}",
        )
    with col2:
        pdf_bytes = generate_certificate_pdf(
            student_name=st.session_state.get("user_name", "Student"),
            event_title=event.get("title", "Event"),
            event_date=format_date(event.get("event_date")),
            cert_type=cert["cert_type"],
        )
        if pdf_bytes:
            st.download_button(
                label="⬇️ PDF",
                data=pdf_bytes,
                file_name=f"certificate_{event.get('title','event').replace(' ','_')}.pdf",
                mime="application/pdf",
                key=f"dl_cert_{cert['id']}",
            )
    st.markdown("<hr style='margin:0.5rem 0;border-color:rgba(166,190,224,0.3);'>", unsafe_allow_html=True)


def render_issue_certificate_form(event_id: str, admin_id: str) -> None:
    """Render admin form to issue a certificate to a participant."""
    from modules.events import get_participants

    participants = get_participants(event_id)
    if not participants:
        st.info("No participants found for this event.")
        return

    user_map = {
        p["users"]["full_name"]: p["user_id"]
        for p in participants if p.get("users")
    }

    with st.form(f"issue_cert_{event_id}"):
        st.subheader("📜 Issue Certificate")
        selected_name = st.selectbox("Select Participant", list(user_map.keys()))
        cert_type = st.selectbox(
            "Certificate Type",
            [CERT_PARTICIPATION, CERT_WINNER, CERT_ORGANIZER],
            format_func=lambda t: t.capitalize(),
        )
        submitted = st.form_submit_button("Issue Certificate", use_container_width=True)

    if submitted:
        uid = user_map[selected_name]
        result = issue_certificate(
            event_id=event_id,
            user_id=uid,
            cert_type=cert_type,
            issued_by=admin_id,
        )
        if result:
            st.success(f"Certificate issued to {selected_name}! 🎉")
        else:
            st.error("Certificate issuance failed.")
