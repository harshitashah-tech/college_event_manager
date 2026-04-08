"""
auth/login.py
-------------
Handles user login via MongoDB + bcrypt password verification.
"""

from __future__ import annotations

import logging

import bcrypt
import streamlit as st

from config import (
    DEMO_LOGIN_EMAIL,
    DEMO_LOGIN_ENABLED,
    DEMO_LOGIN_ID,
    DEMO_LOGIN_NAME,
    DEMO_LOGIN_PASSWORD,
    DEMO_LOGIN_ROLE,
)
from database.mongo_client import get_db
from utils.validators import validate_email

logger = logging.getLogger(__name__)


def login_user(email: str, password: str, demo: bool = False) -> dict | None:
    """
    Authenticate a user against the MongoDB users collection.

    Parameters
    ----------
    email : str
    password : str
    demo : bool
        Whether to use the demo login credentials from configuration.

    Returns
    -------
    dict | None
        User profile dict on success, or None on failure.
        Sets st.session_state keys on success.
    """
    if demo:
        if not DEMO_LOGIN_ENABLED:
            logger.error(
                "Demo login is not configured. Set DEMO_LOGIN_EMAIL and DEMO_LOGIN_PASSWORD in your .env."
            )
            return None

        profile = {
            "id": DEMO_LOGIN_ID,
            "email": DEMO_LOGIN_EMAIL.strip().lower(),
            "full_name": DEMO_LOGIN_NAME,
            "role": DEMO_LOGIN_ROLE,
        }
        _set_session(profile)
        return profile

    email = email.strip().lower()
    err = validate_email(email)
    if err:
        logger.error(err)
        return None

    if not password:
        logger.error("Password is required.")
        return None

    db = get_db()

    user = db.users.find_one({"email": email})
    if not user:
        logger.error("No account found for %s.", email)
        st.error("Invalid email or password.")
        return None

    # Verify password
    try:
        password_valid = bcrypt.checkpw(
            password.encode("utf-8"),
            user["password_hash"].encode("utf-8"),
        )
    except Exception as exc:
        logger.error("Password check error: %s", exc)
        st.error("Login error. Please try again.")
        return None

    if not password_valid:
        st.error("Invalid email or password.")
        return None

    # Normalise _id → id for downstream compatibility
    profile = {**user, "id": user["_id"]}
    profile.pop("password_hash", None)   # never expose hash in session

    _set_session(profile)
    return profile


def _set_session(profile: dict) -> None:
    """Persist user info to Streamlit session state."""
    st.session_state["authenticated"] = True
    st.session_state["user_id"] = profile["id"]
    st.session_state["user_email"] = profile["email"]
    st.session_state["user_role"] = profile["role"]
    st.session_state["user_name"] = profile["full_name"]
    st.session_state["user_profile"] = profile


def logout_user() -> None:
    """Clear all session state (no server-side signout needed)."""
    for key in list(st.session_state.keys()):
        del st.session_state[key]


def render_login_page() -> None:
    """Render the Streamlit login form."""
    from utils.styling import card_container

    st.markdown(
        "<h2 style='text-align:center; color:#2C3E6B;'>Welcome Back</h2>",
        unsafe_allow_html=True,
    )
    st.markdown(
        "<p style='text-align:center; color:#555;'>Sign in to your EventSphere account</p>",
        unsafe_allow_html=True,
    )
    st.markdown("<br>", unsafe_allow_html=True)

    with card_container():
        with st.form("login_form", clear_on_submit=False):
            email = st.text_input("Email", placeholder="you@college.edu", key="login_email")
            password = st.text_input("Password", type="password", placeholder="••••••••", key="login_password")
            submitted = st.form_submit_button("Sign In", use_container_width=True)

        if submitted:
            with st.spinner("Signing in…"):
                result = login_user(email, password)
            if result:
                st.success(f"Welcome, {result['full_name']}!")
                st.rerun()

        if DEMO_LOGIN_ENABLED:
            st.markdown("---")
            st.info("Use demo login for instant access.")
            if st.button("Demo Login", use_container_width=True):
                with st.spinner("Signing in with demo account…"):
                    result = login_user("", "", demo=True)
                if result:
                    st.success(f"Welcome, {result['full_name']}!")
                    st.rerun()
