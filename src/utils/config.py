# src/utils/config.py
"""
Simple configuration management for Medical Schedule Management System.
Keeps all settings in one place with environment variable support.
"""

import os
from datetime import time
from typing import List, Dict, Any

# =============================================================================
# GOOGLE SHEETS CONFIGURATION
# =============================================================================

# Google Sheets Settings
GOOGLE_CREDENTIALS_PATH = os.getenv(
    "GOOGLE_CREDENTIALS_PATH", "config/sanket-medical-credentials.json"
)

GOOGLE_SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

# Sheet Names
DOCTORS_SHEET_NAME = os.getenv("DOCTORS_SHEET_NAME", "sanket_medical_doctors")
SUBMISSIONS_SHEET_NAME = os.getenv(
    "SUBMISSIONS_SHEET_NAME", "sanket_medical_submissions"
)

# API Settings
GOOGLE_SHEETS_TIMEOUT = int(os.getenv("GOOGLE_SHEETS_TIMEOUT", "30"))
GOOGLE_SHEETS_RETRY_ATTEMPTS = int(os.getenv("GOOGLE_SHEETS_RETRY_ATTEMPTS", "3"))
GOOGLE_SHEETS_RATE_LIMIT_DELAY = float(
    os.getenv("GOOGLE_SHEETS_RATE_LIMIT_DELAY", "0.1")
)

# =============================================================================
# BUSINESS RULES CONFIGURATION
# =============================================================================

# Session timing constraints
MIN_SESSION_DURATION_MINUTES = int(os.getenv("MIN_SESSION_DURATION_MINUTES", "30"))
MAX_SESSION_DURATION_MINUTES = int(
    os.getenv("MAX_SESSION_DURATION_MINUTES", "480")
)  # 8 hours
TIME_INCREMENT_MINUTES = int(os.getenv("TIME_INCREMENT_MINUTES", "1"))

# Default session times for UI
DEFAULT_SESSION_START = time(9, 0)  # 9:00 AM
DEFAULT_SESSION_END = time(17, 0)  # 5:00 PM

# Weekend handling
WEEKEND_DAYS = [5, 6]  # Saturday=5, Sunday=6
DEFAULT_WEEKEND_STATUS = "OFF"
MORNING_CUTOFF_TIME = "11:59"  # Sessions before this go to Session 1
OFF_SESSION_PLACEHOLDER = "-"

# Data validation limits
SCRIBE_NAME_MIN_LENGTH = int(os.getenv("SCRIBE_NAME_MIN_LENGTH", "2"))
SCRIBE_NAME_MAX_LENGTH = int(os.getenv("SCRIBE_NAME_MAX_LENGTH", "50"))
PATIENT_NUMBER_MIN = int(os.getenv("PATIENT_NUMBER_MIN", "1"))
PATIENT_NUMBER_MAX = int(os.getenv("PATIENT_NUMBER_MAX", "999999"))

# Maximum sessions per doctor per day
MAX_SESSIONS_PER_DAY = int(os.getenv("MAX_SESSIONS_PER_DAY", "2"))

# =============================================================================
# APPLICATION SETTINGS
# =============================================================================

# App metadata
APP_TITLE = os.getenv("APP_TITLE", "Medical Schedule Management System")
APP_ICON = os.getenv("APP_ICON", "🏥")

# Debug and logging
DEBUG_MODE = os.getenv("DEBUG_MODE", "false").lower() == "true"
LOG_LEVEL = os.getenv("LOG_LEVEL", "DEBUG" if DEBUG_MODE else "INFO")
LOG_TO_FILE = os.getenv("LOG_TO_FILE", "true").lower() == "true"

# =============================================================================
# POC DATA (HARDCODED FOR DEMONSTRATION)
# =============================================================================

# Single Team Leader for POC
POC_TEAM_LEADER = {"id": "TL001", "name": "John Smith", "username": "jsmith"}

# Three doctors from same clinic for POC
POC_DOCTORS = [
    {"id": "DOC001", "clinic": "City Medical Center", "fn": "Sarah", "ln": "Wilson"},
    {"id": "DOC002", "clinic": "City Medical Center", "fn": "Michael", "ln": "Johnson"},
    {"id": "DOC003", "clinic": "City Medical Center", "fn": "Lisa", "ln": "Brown"},
]

# =============================================================================
# DATA STRUCTURE DEFINITIONS
# =============================================================================

# CSV/Sheets column structure for doctors
DOCTORS_COLUMNS = ["doctor_id", "clinic", "fn", "ln", "tl_name", "full_name"]

# CSV/Sheets column structure for submissions
SUBMISSIONS_COLUMNS = [
    "submission_id",
    "doctor_id",
    "doctor_name",
    "date",
    "start_time",
    "end_time",
    "scribe_name",
    "patient_number",
    "submitted_by",
    "submitted_time",
]

# =============================================================================
# UI CONFIGURATION
# =============================================================================

# Streamlit page configuration
STREAMLIT_CONFIG = {
    "page_title": "Medical Schedule Manager",
    "page_icon": APP_ICON,
    "layout": "wide",
    "initial_sidebar_state": "collapsed",
}

# Button and label text
LABELS = {
    "team_leader_selection": "Select Team Leader:",
    "doctor_selection": "👨‍⚕️ Select Doctor:",
    "date_selection": "📅 Select Date:",
    "start_time": "🕐 Start Time:",
    "end_time": "🕐 End Time:",
    "scribe_name": "👤 Scribe Name:",
    "patient_number": "🏥 Patient Number:",
    "add_session": "➕ Add Session",
    "submit_sessions": "✅ Submit {count} Sessions",
    "edit_session": "✏️ Edit",
    "delete_session": "🗑️ Delete",
    "weekend_override": "🏖️ Override Weekend",
}

# Success messages
SUCCESS_MESSAGES = {
    "session_added": "✅ Session added to draft!",
    "sessions_submitted": "✅ Successfully submitted {count} sessions!",
    "session_updated": "✅ Session updated successfully!",
    "session_deleted": "✅ Session deleted successfully!",
}

# Error messages
ERROR_MESSAGES = {
    "time_overlap": "⚠️ Session overlaps with existing session!",
    "invalid_time": "⚠️ End time must be after start time!",
    "session_too_short": f"⚠️ Session must be at least {MIN_SESSION_DURATION_MINUTES} minutes!",
    "session_too_long": f"⚠️ Session cannot exceed {MAX_SESSION_DURATION_MINUTES} minutes!",
    "invalid_scribe_name": f"⚠️ Scribe name must be {SCRIBE_NAME_MIN_LENGTH}-{SCRIBE_NAME_MAX_LENGTH} characters!",
    "invalid_patient_number": f"⚠️ Patient number must be between {PATIENT_NUMBER_MIN}-{PATIENT_NUMBER_MAX}!",
    "missing_required_field": "⚠️ All fields are required!",
    "no_sessions_to_submit": "⚠️ No sessions to submit!",
    "submission_failed": "❌ Failed to submit sessions. Please try again.",
    "daily_limit_exceeded": f"⚠️ Cannot exceed {MAX_SESSIONS_PER_DAY} sessions per day!",
    "google_sheets_error": "❌ Error connecting to Google Sheets. Please try again.",
    "network_error": "❌ Network error. Please check your connection and try again.",
}

# Info messages
INFO_MESSAGES = {
    "weekend_default": '🏖️ Weekends are OFF by default. Click "Override Weekend" to add sessions.',
    "weekend_override_enabled": "🏖️ Weekend override enabled. You can now add sessions.",
    "draft_mode": "💾 Sessions are in DRAFT mode. Remember to submit when complete.",
    "no_sessions": "📝 No sessions scheduled for this date.",
    "review_sessions": "👀 Review your sessions below, then submit when ready.",
}

# =============================================================================
# HELPER FUNCTIONS
# =============================================================================


def get_google_credentials_path() -> str:
    """Get the path to Google credentials file."""
    return GOOGLE_CREDENTIALS_PATH


def get_streamlit_config() -> Dict[str, Any]:
    """Get Streamlit page configuration."""
    return STREAMLIT_CONFIG


def is_debug_mode() -> bool:
    """Check if debug mode is enabled."""
    return DEBUG_MODE


def get_poc_doctors() -> List[Dict[str, str]]:
    """Get list of POC doctors."""
    return POC_DOCTORS.copy()


def get_poc_team_leader() -> Dict[str, str]:
    """Get POC team leader information."""
    return POC_TEAM_LEADER.copy()


def validate_environment() -> bool:
    """
    Validate that required environment settings are available.

    Returns:
        True if environment is valid, False otherwise
    """
    # Check if credentials file exists
    if not os.path.exists(GOOGLE_CREDENTIALS_PATH):
        print(
            f"WARNING: Google credentials file not found at {GOOGLE_CREDENTIALS_PATH}"
        )
        return False

    # Basic validation of business rules
    if MIN_SESSION_DURATION_MINUTES >= MAX_SESSION_DURATION_MINUTES:
        print("ERROR: Invalid session duration configuration")
        return False

    if MAX_SESSIONS_PER_DAY < 1:
        print("ERROR: Max sessions per day must be at least 1")
        return False

    return True
