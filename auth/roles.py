"""
auth/roles.py
-------------
Role constants and permission helpers.
"""

from config import ROLE_ADMIN, ROLE_COORDINATOR, ROLE_STUDENT


def is_admin(role: str) -> bool:
    """Return True if the given role string is admin."""
    return role == ROLE_ADMIN


def is_coordinator(role: str) -> bool:
    """Return True if the given role string is coordinator."""
    return role == ROLE_COORDINATOR


def is_student(role: str) -> bool:
    """Return True if the given role string is student."""
    return role == ROLE_STUDENT


def can_manage_events(role: str) -> bool:
    """Coordinators and admins can create/edit events."""
    return role in (ROLE_COORDINATOR, ROLE_ADMIN)


def can_approve(role: str) -> bool:
    """Only admins can approve events and clubs."""
    return role == ROLE_ADMIN


def role_label(role: str) -> str:
    """Return a human-friendly label for the role."""
    labels = {
        ROLE_STUDENT: "🎓 Student",
        ROLE_COORDINATOR: "🎯 Club Coordinator",
        ROLE_ADMIN: "🛡️ Administrator",
    }
    return labels.get(role, role.capitalize())
