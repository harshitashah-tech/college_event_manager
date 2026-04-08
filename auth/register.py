"""
auth/register.py
----------------
Handles new user registration using MongoDB + bcrypt password hashing.
"""

from __future__ import annotations

import uuid

import bcrypt
import streamlit as st

from config import ALL_ROLES
from database.mongo_client import get_db
from utils.validators import validate_email, validate_password, validate_required


def register_user(
    email: str,
    password: str,
    full_name: str,
    role: str,
    department: str,
    year_of_study: int | None,
    phone: str,
) -> bool:
    """
    Create a new user document in MongoDB with a hashed password.

    Returns
    -------
    bool
        True on success, False on failure.
    """
    db = get_db()

    # ── Validation ────────────────────────────────────────────────────────────
    for field_val, field_name in [
        (full_name, "Full name"),
        (email, "Email"),
        (password, "Password"),
        (department, "Department"),
    ]:
        err = validate_required(field_val, field_name)
        if err:
            st.error(err)
            return False

    err = validate_email(email.strip().lower())
    if err:
        st.error(err)
        return False

    err = validate_password(password)
    if err:
        st.error(err)
        return False

    email_lower = email.strip().lower()

    # ── Check for duplicate email ─────────────────────────────────────────────
    if db.users.find_one({"email": email_lower}):
        st.error("An account with this email already exists.")
        return False

    # ── Hash password ─────────────────────────────────────────────────────────
    hashed_pw = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

    # ── Insert user document ──────────────────────────────────────────────────
    user_doc = {
        "_id": str(uuid.uuid4()),
        "full_name": full_name.strip(),
        "email": email_lower,
        "password_hash": hashed_pw,
        "role": role,
        "department": department.strip(),
        "year_of_study": year_of_study,
        "phone": phone.strip() if phone else None,
        "avatar_url": None,
        "created_at": __import__("datetime").datetime.utcnow().isoformat(),
        "updated_at": __import__("datetime").datetime.utcnow().isoformat(),
    }

    try:
        db.users.insert_one(user_doc)
    except Exception as exc:
        st.error(f"Registration failed: {exc}")
        return False

    return True


def render_register_page() -> None:
    """Render the Streamlit registration form."""
    from utils.styling import card_container

    st.markdown(
        "<h2 style='text-align:center; color:#2C3E6B;'>Create Your Account</h2>",
        unsafe_allow_html=True,
    )
    st.markdown(
        "<p style='text-align:center; color:#555;'>Join EventSphere — discover and manage college events</p>",
        unsafe_allow_html=True,
    )
    st.markdown("<br>", unsafe_allow_html=True)

    with card_container():
        with st.form("register_form", clear_on_submit=False):
            col1, col2 = st.columns(2)
            with col1:
                full_name = st.text_input("Full Name", placeholder="Jane Doe")
                email = st.text_input("College Email", placeholder="jane@college.edu")
                password = st.text_input("Password", type="password", placeholder="Min 8 chars")
            with col2:
                role = st.selectbox(
                    "🎭 Role",
                    options=["student", "coordinator"],
                    format_func=lambda r: "Student" if r == "student" else "🎯 Coordinator",
                )
                department = st.text_input("Department", placeholder="Computer Science")
                year_of_study = st.selectbox(
                    "Year of Study",
                    options=[None, 1, 2, 3, 4],
                    format_func=lambda y: "N/A" if y is None else f"Year {y}",
                )

            phone = st.text_input("Phone (optional)", placeholder="+91 98765 43210")

            submitted = st.form_submit_button("Create Account", use_container_width=True)

        if submitted:
            with st.spinner("Creating your account…"):
                success = register_user(
                    email=email,
                    password=password,
                    full_name=full_name,
                    role=role,
                    department=department,
                    year_of_study=year_of_study if year_of_study else None,
                    phone=phone,
                )
            if success:
                st.success("Account created! You can now sign in.")
                st.info("Switch to the **Login** tab to sign in.")
