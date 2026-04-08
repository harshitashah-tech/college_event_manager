"""
config.py
---------
Central configuration for the College Event Management System.
Loads environment variables from .env file for MongoDB credentials.
"""

import os
from dotenv import load_dotenv

load_dotenv(override=True)

# ── MongoDB ───────────────────────────────────────────────────────────────────
MONGO_URI: str = os.getenv("MONGO_URI", "mongodb://localhost:27017")
MONGO_DB_NAME: str = os.getenv("MONGO_DB_NAME", "college_event_manager")

# ── Demo Login (optional) ──────────────────────────────────────────────────────
DEMO_LOGIN_EMAIL: str = os.getenv("DEMO_LOGIN_EMAIL", "")
DEMO_LOGIN_PASSWORD: str = os.getenv("DEMO_LOGIN_PASSWORD", "")
DEMO_LOGIN_NAME: str = os.getenv("DEMO_LOGIN_NAME", "Demo User")
DEMO_LOGIN_ROLE: str = os.getenv("DEMO_LOGIN_ROLE", "student")
DEMO_LOGIN_ID: str = os.getenv("DEMO_LOGIN_ID", "demo-user")
DEMO_LOGIN_ENABLED: bool = bool(DEMO_LOGIN_EMAIL and DEMO_LOGIN_PASSWORD)

# ── App Meta ──────────────────────────────────────────────────────────────────
APP_NAME: str = "EventSphere"
APP_TAGLINE: str = "Your College Event Hub"
APP_VERSION: str = "1.0.0"

# ── Roles ─────────────────────────────────────────────────────────────────────
ROLE_STUDENT: str = "student"
ROLE_COORDINATOR: str = "coordinator"
ROLE_ADMIN: str = "admin"
ALL_ROLES: list[str] = [ROLE_STUDENT, ROLE_COORDINATOR, ROLE_ADMIN]

# ── Event Categories ─────────────────────────────────────────────────────────
EVENT_CATEGORIES: list[str] = [
    "Technical",
    "Cultural",
    "Sports",
    "Workshop",
    "Seminar",
    "Hackathon",
    "Arts",
    "Other",
]

# ── Payment Statuses ─────────────────────────────────────────────────────────
PAYMENT_PENDING: str = "pending"
PAYMENT_PAID: str = "paid"
PAYMENT_FAILED: str = "failed"

# ── Event Approval Statuses ──────────────────────────────────────────────────
STATUS_PENDING: str = "pending"
STATUS_APPROVED: str = "approved"
STATUS_REJECTED: str = "rejected"

# ── Certificate Types ─────────────────────────────────────────────────────────
CERT_PARTICIPATION: str = "participation"
CERT_WINNER: str = "winner"
CERT_ORGANIZER: str = "organizer"

# ── Pagination ────────────────────────────────────────────────────────────────
PAGE_SIZE: int = 10

# ── Recommendation Weights ────────────────────────────────────────────────────
REC_CLUB_MATCH_SCORE: int = 3
REC_CATEGORY_MATCH_SCORE: int = 2
REC_PAST_REGISTRATION_SCORE: int = 1
