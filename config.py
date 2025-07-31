# config.py - Medical Schedule Management System Configuration
# CONFIGURATION ONLY - No functions, no business logic, just settings

import os
from datetime import time

# =============================================================================
# FILE PATHS AND DATA CONFIGURATION
# =============================================================================

# Base data folder
DATA_FOLDER = "data/"

# Single CSV file for all submissions (simplified architecture)
SUBMISSIONS_FILE = f"{DATA_FOLDER}submissions.csv"

# Ensure data directory exists
if not os.path.exists(DATA_FOLDER):
    os.makedirs(DATA_FOLDER)

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
# BUSINESS RULES AND VALIDATION
# =============================================================================

# Session timing constraints
MIN_SESSION_DURATION_MINUTES = 30  # Minimum session length
MAX_SESSION_DURATION_MINUTES = 480  # Maximum session length (8 hours)
TIME_INCREMENT_MINUTES = 1  # 1-minute precision (per client request)

# Default session times for UI
DEFAULT_SESSION_START = time(9, 0)  # 9:00 AM
DEFAULT_SESSION_END = time(17, 0)  # 5:00 PM

# Weekend handling
WEEKEND_DAYS = [5, 6]  # Saturday=5, Sunday=6
DEFAULT_WEEKEND_STATUS = "OFF"  # Weekends default to off

# Data validation limits
SCRIBE_NAME_MIN_LENGTH = 2  # Minimum scribe name length
SCRIBE_NAME_MAX_LENGTH = 50  # Maximum scribe name length
PATIENT_NUMBER_MIN = 1  # Minimum patient number
PATIENT_NUMBER_MAX = 999999  # Maximum patient number

# Maximum sessions per doctor per day
MAX_SESSIONS_PER_DAY = 2  # Maximum sessions per doctor per day
MORNING_CUTOFF_TIME = "11:59"  # Sessions before this go to Session 1
OFF_SESSION_PLACEHOLDER = "-"  # What to put in off session fields

# =============================================================================
# APPLICATION SETTINGS
# =============================================================================

# App metadata
APP_TITLE = "Medical Schedule Management System"
APP_ICON = "🏥"

# CSV column structure for submissions.csv
SUBMISSIONS_CSV_COLUMNS = [
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
    "missing_required_field": "⚠️ All fields are required!",
    "empty_patient_number": "⚠️ Patient number is required and cannot be empty!",
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
# DEVELOPMENT SETTINGS
# =============================================================================

# Debug flags (for development)
DEBUG_MODE = False
VERBOSE_LOGGING = False
ENABLE_DEBUG_PANEL = DEBUG_MODE

# Sample data for testing (if needed)
SAMPLE_SESSIONS = [
    {
        "doctor_id": "DOC001",
        "date": "2025-07-28",
        "start_time": "09:00",
        "end_time": "12:00",
        "scribe_name": "Alice Brown",
        "patient_number": 12345,
    },
    {
        "doctor_id": "DOC001",
        "date": "2025-07-28",
        "start_time": "14:00",
        "end_time": "17:00",
        "scribe_name": "Bob Smith",
        "patient_number": 67890,
    },
]
