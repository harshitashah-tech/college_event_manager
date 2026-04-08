"""
modules/payments.py
-------------------
Simulated payment processing (sandbox only — no real gateway) — MongoDB version.
"""

from __future__ import annotations

import random
import uuid
from datetime import datetime

import streamlit as st

from config import PAYMENT_PAID, PAYMENT_FAILED, PAYMENT_PENDING
from database.mongo_client import get_db
from utils.helpers import generate_transaction_ref, format_currency, format_datetime


# ═══════════════════════════════════════════════════════════════
#  CRUD
# ═══════════════════════════════════════════════════════════════

def create_payment_record(
    registration_id: str,
    user_id: str,
    event_id: str,
    amount: float,
) -> dict | None:
    """Insert a pending payment document when a student registers for a paid event."""
    db = get_db()
    doc = {
        "_id": str(uuid.uuid4()),
        "registration_id": registration_id,
        "user_id": user_id,
        "event_id": event_id,
        "amount": amount,
        "status": PAYMENT_PENDING,
        "transaction_ref": generate_transaction_ref(),
        "paid_at": None,
        "created_at": datetime.utcnow().isoformat(),
    }
    try:
        db.payments.insert_one(doc)
        return {**doc, "id": doc["_id"]}
    except Exception as exc:
        st.error(f"Payment record creation failed: {exc}")
        return None


def simulate_payment(payment_id: str) -> str:
    """
    Simulate a payment attempt.

    90% → paid, 10% → failed. Returns the resulting status string.
    """
    db = get_db()
    outcome = PAYMENT_PAID if random.random() < 0.90 else PAYMENT_FAILED
    updates: dict = {"status": outcome}
    if outcome == PAYMENT_PAID:
        updates["paid_at"] = datetime.utcnow().isoformat()

    try:
        db.payments.update_one({"_id": payment_id}, {"$set": updates})
    except Exception as exc:
        st.error(f"Payment simulation error: {exc}")
        return PAYMENT_FAILED

    return outcome


def get_payment_for_registration(registration_id: str) -> dict | None:
    """Return the payment document linked to a registration."""
    db = get_db()
    try:
        doc = db.payments.find_one({"registration_id": registration_id})
        return {**doc, "id": doc["_id"]} if doc else None
    except Exception:
        return None


def get_user_payments(user_id: str) -> list[dict]:
    """Fetch all payment documents for a user, joined with event details."""
    db = get_db()
    try:
        raw = list(db.payments.find({"user_id": user_id}).sort("created_at", -1))
        result = []
        for p in raw:
            event = db.events.find_one({"_id": p["event_id"]}, {"title": 1, "event_date": 1})
            result.append({
                **p,
                "id": p["_id"],
                "events": {**event, "id": event["_id"]} if event else None,
            })
        return result
    except Exception as exc:
        st.error(f"Failed to load payments: {exc}")
        return []


def get_all_transactions() -> list[dict]:
    """Admin view — all payment documents with user and event info."""
    db = get_db()
    try:
        raw = list(db.payments.find().sort("created_at", -1))
        result = []
        for p in raw:
            user = db.users.find_one({"_id": p["user_id"]}, {"full_name": 1, "email": 1})
            event = db.events.find_one({"_id": p["event_id"]}, {"title": 1})
            result.append({
                **p,
                "id": p["_id"],
                "users": {**user, "id": user["_id"]} if user else None,
                "events": {**event, "id": event["_id"]} if event else None,
            })
        return result
    except Exception as exc:
        st.error(f"Failed to load transactions: {exc}")
        return []


def get_payment_stats() -> dict:
    """Return aggregate payment stats for admin dashboard."""
    transactions = get_all_transactions()
    total_collected = sum(t["amount"] for t in transactions if t["status"] == PAYMENT_PAID)
    return {
        "total": len(transactions),
        "paid": sum(1 for t in transactions if t["status"] == PAYMENT_PAID),
        "pending": sum(1 for t in transactions if t["status"] == PAYMENT_PENDING),
        "failed": sum(1 for t in transactions if t["status"] == PAYMENT_FAILED),
        "total_collected": total_collected,
    }


# ═══════════════════════════════════════════════════════════════
#  UI COMPONENTS
# ═══════════════════════════════════════════════════════════════

def render_payment_widget(registration: dict, event: dict) -> None:
    """Render a payment widget for a specific registration."""
    from utils.helpers import status_badge

    reg_id = registration["id"]
    payment = get_payment_for_registration(reg_id)

    if not payment:
        st.info("No payment record found for this registration.")
        return

    st.markdown(
        f"**Transaction Ref:** `{payment.get('transaction_ref','—')}`  \n"
        f"**Amount:** {format_currency(payment.get('amount', 0))}  \n"
        f"**Status:** {payment.get('status','—').upper()}",
        unsafe_allow_html=False,
    )

    if payment["status"] == PAYMENT_PENDING:
        if st.button(
            f"💳 Pay {format_currency(payment['amount'])}",
            key=f"pay_{payment['id']}",
            type="primary",
        ):
            with st.spinner("Processing payment…"):
                outcome = simulate_payment(payment["id"])
            if outcome == PAYMENT_PAID:
                st.success("✅ Payment successful!")
                st.rerun()
            else:
                st.error("❌ Payment failed. Please try again.")
                st.rerun()

    elif payment["status"] == PAYMENT_PAID:
        st.success(f"✅ Paid on {format_datetime(payment.get('paid_at'))}")
    else:
        st.error("❌ Payment failed")
        if st.button("Retry Payment", key=f"retry_{payment['id']}"):
            db = get_db()
            db.payments.update_one({"_id": payment["id"]}, {"$set": {"status": PAYMENT_PENDING}})
            st.rerun()
