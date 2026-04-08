"""
app.py
------
Main entry point for the EventSphere College Event Management System.

Run with:
    streamlit run app.py
"""

import streamlit as st

# ── Page configuration (must be FIRST Streamlit call) ────────────────────────
st.set_page_config(
    page_title="EventSphere | College Event Manager",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Apply global styling ──────────────────────────────────────────────────────
from utils.styling import inject_global_css
inject_global_css()

# ── Auth imports ──────────────────────────────────────────────────────────────
from auth.login    import render_login_page
from auth.register import render_register_page
from auth.roles    import role_label
from config        import ROLE_STUDENT, ROLE_COORDINATOR, ROLE_ADMIN


# ─────────────────────────────────────────────────────────────────────────────
#  SESSION STATE INITIALISATION
# ─────────────────────────────────────────────────────────────────────────────

def _init_session() -> None:
    """Initialise required session state keys if they don't already exist."""
    defaults = {
        "authenticated": False,
        "user_id":       None,
        "user_email":    None,
        "user_role":     None,
        "user_name":     None,
        "user_profile":  None,
        "student_page":  "Dashboard",
        "coord_page":    "Dashboard",
        "admin_page":    "Dashboard",
    }
    for key, val in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = val


# ─────────────────────────────────────────────────────────────────────────────
#  AUTH GATE
# ─────────────────────────────────────────────────────────────────────────────

def render_auth_page() -> None:
    """
    Display the login / register screen.
    Uses tabs so the user can switch between them without page navigation.
    """
    # Centred header
    col_l, col_c, col_r = st.columns([1, 3, 1])
    with col_c:
        st.markdown(
            """
            <div style='text-align:center; padding: 2rem 0 1rem 0;'>
                <div style='font-size:3rem;'>🎓</div>
                <h1 style='font-family:"DM Serif Display",serif;
                            color:#2C3E6B; margin:0.2rem 0;'>
                    EventSphere
                </h1>
                <p style='color:#7E8BB1; font-size:1rem; margin:0;'>
                    Your College Event Management Hub
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )

        tab_login, tab_register = st.tabs(["🔑 Sign In", "📝 Register"])
        with tab_login:
            render_login_page()
        with tab_register:
            render_register_page()


# ─────────────────────────────────────────────────────────────────────────────
#  ROLE ROUTING
# ─────────────────────────────────────────────────────────────────────────────

def route_to_dashboard() -> None:
    """
    Route the authenticated user to the correct role-based dashboard.
    """
    role = st.session_state.get("user_role", "")

    if role == ROLE_STUDENT:
        from dashboards.student_dashboard import render_student_dashboard
        render_student_dashboard()

    elif role == ROLE_COORDINATOR:
        from dashboards.coordinator_dashboard import render_coordinator_dashboard
        render_coordinator_dashboard()

    elif role == ROLE_ADMIN:
        from dashboards.admin_dashboard import render_admin_dashboard
        render_admin_dashboard()

    else:
        st.error(
            f"Unknown role '{role}'. Please contact an administrator "
            "or try logging in again."
        )
        if st.button("Back to Login"):
            from auth.login import logout_user
            logout_user()
            st.rerun()


# ─────────────────────────────────────────────────────────────────────────────
#  MAIN
# ─────────────────────────────────────────────────────────────────────────────

def main() -> None:
    _init_session()

    if st.session_state["authenticated"]:
        route_to_dashboard()
    else:
        render_auth_page()


if __name__ == "__main__":
    main()
