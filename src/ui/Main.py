# src/ui/pages/main.py
"""
Main Medical Schedule Management System Application

Clean, single-page interface focused on core scheduling workflow
with proper logging and modular architecture.
"""

import sys
import os
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

import streamlit as st
from datetime import datetime, date, time
from typing import Dict, List, Any, Optional

# Import our modular components - using relative imports from project root
try:
    from src.utils.logging_config import get_logger, setup_logging
    from src.utils.config import (
        APP_TITLE,
        APP_ICON,
        STREAMLIT_CONFIG,
        POC_TEAM_LEADER,
        POC_DOCTORS,
        LABELS,
        SUCCESS_MESSAGES,
        ERROR_MESSAGES,
        INFO_MESSAGES,
        MAX_SESSIONS_PER_DAY,
        get_streamlit_config,
        is_debug_mode,
    )
    from src.infrastructure.sheets.sheets_ops import (
        load_submissions,
        save_sessions_to_sheets,
        get_existing_sessions,
        get_day_summary,
        format_doctor_name,
        update_submission,
        delete_submission,
        validate_sheets_connection,
        get_sheets_stats,
    )
    from src.infrastructure.auth.google_auth import (
        test_google_authentication,
        validate_google_setup,
    )
except ImportError as e:
    print(f"Import error: {e}")
    print("Please ensure you're running from the project root directory")
    print("Current working directory:", os.getcwd())
    print("Project root should be:", project_root)
    sys.exit(1)

# Import validation functions - we'll handle this separately since validation.py might still be in old location
try:
    from src.core.validators.validation import (
        validate_session_data,
        check_session_overlap,
        validate_draft_sessions,
        is_weekend,
        get_weekend_info,
        validate_submission_readiness,
        check_daily_session_limit,
    )
except ImportError:
    # Fallback to old location if validation hasn't been moved yet
    try:
        from validation import (
            validate_session_data,
            check_session_overlap,
            validate_draft_sessions,
            is_weekend,
            get_weekend_info,
            validate_submission_readiness,
            check_daily_session_limit,
        )

        print(
            "Warning: Using validation.py from old location. Please move to src/core/validators/"
        )
    except ImportError as e:
        print(f"Could not import validation functions: {e}")
        print(
            "Please ensure validation.py is in src/core/validators/ or current directory"
        )
        sys.exit(1)

# Initialize logging
setup_logging()
logger = get_logger(__name__)

# =============================================================================
# APPLICATION INITIALIZATION
# =============================================================================


# def setup_streamlit_app() -> None:
#     """Configure Streamlit app with proper settings and validation"""
#     logger.info("Setting up Streamlit application...")

#     try:
#         # Configure Streamlit
#         config = get_streamlit_config()
#         st.set_page_config(**config)
#         logger.info("Streamlit configuration applied successfully")

#         # Validate Google Sheets connection on startup
#         if not validate_google_connection():
#             st.error("❌ Google Sheets connection failed. Check logs for details.")
#             logger.error("Google Sheets connection validation failed - stopping app")
#             st.stop()

#     except Exception as e:
#         logger.error(f"Failed to setup Streamlit app: {str(e)}")
#         st.error(f"❌ Application setup failed: {str(e)}")
#         st.stop()


def setup_streamlit_app() -> None:
    """Configure Streamlit app with proper settings (NO connection testing)"""
    logger.info("Setting up Streamlit application...")

    try:
        # Configure Streamlit
        config = get_streamlit_config()
        st.set_page_config(**config)
        logger.info("Streamlit configuration applied successfully")

        # REMOVED: Connection validation - now happens lazily when needed

    except Exception as e:
        logger.error(f"Failed to setup Streamlit app: {str(e)}")
        st.error(f"❌ Application setup failed: {str(e)}")
        st.stop()


# def validate_google_connection() -> bool:
#     """
#     Validate Google Sheets connection and display status.

#     Returns:
#         True if connection is valid, False otherwise
#     """
#     logger.info("Validating Google Sheets connection...")

#     try:
#         # Test authentication
#         auth_success, auth_message = test_google_authentication()
#         if not auth_success:
#             logger.error(f"Google authentication failed: {auth_message}")
#             st.error(f"Google Authentication Error: {auth_message}")
#             return False

#         # Test actual sheets connection
#         if not validate_sheets_connection():
#             logger.error("Sheets connection validation failed")
#             st.error("Google Sheets connection failed")
#             return False

#         logger.info("Google Sheets connection validation successful")
#         return True

#     except Exception as e:
#         logger.error(f"Error during Google connection validation: {str(e)}")
#         st.error(f"Connection validation error: {str(e)}")
#         return False


def initialize_session_state() -> None:
    """Initialize Streamlit session state variables"""
    logger.info("Initializing session state...")

    # Initialize draft sessions
    if "draft_sessions" not in st.session_state:
        st.session_state.draft_sessions = []
        logger.debug("Initialized draft_sessions")

    # Initialize selected doctor
    if "selected_doctor" not in st.session_state:
        st.session_state.selected_doctor = None
        logger.debug("Initialized selected_doctor")

    # Initialize selected date
    if "selected_date" not in st.session_state:
        st.session_state.selected_date = date.today()
        logger.debug(f"Initialized selected_date: {st.session_state.selected_date}")

    logger.info("Session state initialization complete")


# =============================================================================
# HEADER AND SELECTION COMPONENTS
# =============================================================================


def render_application_header() -> None:
    """Render the main application header with title and status"""
    logger.debug("Rendering application header")

    st.title(f"{APP_ICON} {APP_TITLE}")

    # Show connection status
    render_connection_status_inline()

    # Show debug info if enabled
    if is_debug_mode():
        with st.expander("🔧 Debug Information", expanded=False):
            render_debug_info()


# def render_connection_status_inline() -> None:
#     """Render connection status inline"""
#     try:
#         col1, col2, col3 = st.columns([3, 1, 1])

#         with col2:
#             if st.button("🔄 Test Connection", use_container_width=True):
#                 test_and_display_connection()

#         with col3:
#             # Show current status
#             stats = get_sheets_stats()
#             if stats["connection_status"] == "Connected":
#                 st.success("✅ Connected")
#             else:
#                 st.error("❌ Disconnected")

#     except Exception as e:
#         logger.error(f"Error rendering connection status: {str(e)}")


def render_connection_status_inline() -> None:
    """Render connection status inline - but make it manual"""
    try:
        col1, col2, col3 = st.columns([3, 1, 1])

        with col2:
            if st.button("🔄 Test Connection", use_container_width=True):
                test_and_display_connection()

        with col3:
            # Show cached status if available
            if "connection_status" in st.session_state:
                if st.session_state.connection_status:
                    st.success("✅ Connected")
                else:
                    st.error("❌ Disconnected")
            else:
                st.info("❓ Not Tested")

    except Exception as e:
        logger.error(f"Error rendering connection status: {str(e)}")


# def test_and_display_connection() -> None:
#     """Test and display connection status"""
#     logger.info("Testing Google Sheets connection...")

#     with st.spinner("Testing connection..."):
#         is_connected, message = test_google_authentication()

#         if is_connected:
#             st.success(f"✅ {message}")
#             logger.info("Connection test successful")
#         else:
#             st.error(f"❌ {message}")
#             logger.error(f"Connection test failed: {message}")


def test_and_display_connection() -> None:
    """Test and display connection status - cache the result"""
    logger.info("Manual connection test requested")

    with st.spinner("Testing connection..."):
        try:
            # Test the connection
            is_connected, message = test_google_authentication()

            # Cache the result
            st.session_state.connection_status = is_connected

            if is_connected:
                st.success(f"✅ {message}")
                logger.info("Manual connection test successful")
            else:
                st.error(f"❌ {message}")
                logger.error(f"Manual connection test failed: {message}")

        except Exception as e:
            st.session_state.connection_status = False
            st.error(f"❌ Connection test error: {str(e)}")
            logger.error(f"Connection test exception: {str(e)}")


def render_debug_info() -> None:
    """Render debug information for development"""
    logger.debug("Rendering debug information")

    try:
        # Google Sheets stats
        stats = get_sheets_stats()
        st.json(
            {
                "google_sheets_stats": stats,
                "session_state": {
                    "draft_sessions_count": len(st.session_state.draft_sessions),
                    "selected_doctor": (
                        st.session_state.selected_doctor["id"]
                        if st.session_state.selected_doctor
                        else None
                    ),
                    "selected_date": str(st.session_state.selected_date),
                },
                "system_info": {
                    "project_root": str(project_root),
                    "current_working_directory": os.getcwd(),
                    "python_path": sys.path[:3],  # First 3 entries
                },
            }
        )

    except Exception as e:
        st.error(f"Debug info error: {str(e)}")
        logger.error(f"Error rendering debug info: {str(e)}")


def render_doctor_date_selection() -> tuple[Optional[Dict], date, bool]:
    """
    Render doctor and date selection interface.

    Returns:
        Tuple of (selected_doctor, selected_date, weekend_override)
    """
    logger.debug("Rendering doctor and date selection")

    # Create columns for selections
    col1, col2, col3 = st.columns([2, 2, 1])

    with col1:
        # Doctor selection
        doctor_options = [format_doctor_name(doc) for doc in POC_DOCTORS]
        selected_doctor_name = st.selectbox(
            LABELS["doctor_selection"], options=doctor_options, key="doctor_selector"
        )

        # Find selected doctor info
        selected_doctor = find_doctor_by_name(selected_doctor_name)
        st.session_state.selected_doctor = selected_doctor

        logger.debug(
            f"Selected doctor: {selected_doctor['id'] if selected_doctor else None}"
        )

    with col2:
        # Date selection with draft session handling
        selected_date = render_date_selection()
        logger.debug(f"Selected date: {selected_date}")

    with col3:
        # Weekend override
        weekend_override = render_weekend_override(selected_date)
        logger.debug(f"Weekend override: {weekend_override}")

    return selected_doctor, selected_date, weekend_override


def find_doctor_by_name(doctor_name: str) -> Optional[Dict]:
    """
    Find doctor info by formatted name.

    Args:
        doctor_name: Formatted doctor name

    Returns:
        Doctor dictionary or None
    """
    for doc in POC_DOCTORS:
        if format_doctor_name(doc) == doctor_name:
            return doc
    return None


def render_date_selection() -> date:
    """
    Render date selection with draft session awareness.

    Returns:
        Selected date
    """
    has_drafts = bool(st.session_state.draft_sessions)

    if has_drafts:
        # Show disabled date input with explanation
        st.date_input(
            LABELS["date_selection"],
            value=st.session_state.selected_date,
            key="date_selector_disabled",
            disabled=True,
            help="Date selection is disabled while you have unsaved draft sessions",
        )

        # Show warning and action needed
        st.warning(
            f"⚠️ You have {len(st.session_state.draft_sessions)} unsaved draft session(s)"
        )
        st.info(
            "💡 Please **Submit** your sessions or **Delete** them to change the date"
        )

        # Emergency clear button
        if st.button(
            "🗑️ Clear All Draft Sessions", type="secondary", use_container_width=True
        ):
            clear_all_draft_sessions()

    else:
        # Normal date selection when no drafts
        selected_date = st.date_input(
            LABELS["date_selection"],
            value=st.session_state.selected_date,
            key="date_selector",
        )
        st.session_state.selected_date = selected_date

    return st.session_state.selected_date


def render_weekend_override(selected_date: date) -> bool:
    """
    Render weekend override checkbox if needed.

    Args:
        selected_date: Currently selected date

    Returns:
        Weekend override status
    """
    weekend_override = False

    if is_weekend(selected_date):
        weekend_info = get_weekend_info(selected_date)
        st.info(f"🏖️ {weekend_info['day_name']} is a weekend")
        weekend_override = st.checkbox(
            "Override Weekend", help="Allow scheduling on weekends"
        )
        logger.debug(f"Weekend override for {selected_date}: {weekend_override}")

    return weekend_override


def clear_all_draft_sessions() -> None:
    """Clear all draft sessions and refresh the app"""
    logger.info("Clearing all draft sessions")

    session_count = len(st.session_state.draft_sessions)
    st.session_state.draft_sessions = []

    st.success(
        f"✅ Cleared {session_count} draft sessions! You can now change the date."
    )
    logger.info(f"Cleared {session_count} draft sessions")
    st.rerun()


# =============================================================================
# SESSION ENTRY FORM
# =============================================================================


def render_add_session_form(
    doctor: Dict, selected_date: date, weekend_override: bool
) -> None:
    """
    Render the add session form with validation and limits checking.

    Args:
        doctor: Selected doctor information
        selected_date: Selected date
        weekend_override: Weekend override status
    """
    logger.debug(
        f"Rendering add session form for doctor {doctor['id']}, date {selected_date}"
    )

    # Check if we can add sessions
    if not can_add_sessions(selected_date, weekend_override):
        return

    # Check daily session limits
    if not check_session_limits(doctor, selected_date):
        return

    st.subheader("➕ Add Session")

    with st.container(border=True):
        render_session_form_fields(doctor, selected_date)


def can_add_sessions(selected_date: date, weekend_override: bool) -> bool:
    """
    Check if sessions can be added for the selected date.

    Args:
        selected_date: Selected date
        weekend_override: Weekend override status

    Returns:
        True if sessions can be added
    """
    if is_weekend(selected_date) and not weekend_override:
        st.warning(INFO_MESSAGES["weekend_default"])
        logger.debug(f"Cannot add sessions - weekend without override: {selected_date}")
        return False

    return True


def check_session_limits(doctor: Dict, selected_date: date) -> bool:
    """
    Check and display session limit information.

    Args:
        doctor: Doctor information
        selected_date: Selected date

    Returns:
        True if more sessions can be added
    """
    try:
        existing_sessions = get_existing_sessions(
            doctor["id"], selected_date.strftime("%Y-%m-%d")
        )
        current_total = len(existing_sessions) + len(st.session_state.draft_sessions)
        sessions_remaining = MAX_SESSIONS_PER_DAY - current_total

        logger.debug(
            f"Session limits check: existing={len(existing_sessions)}, drafts={len(st.session_state.draft_sessions)}, remaining={sessions_remaining}"
        )

        if sessions_remaining <= 0:
            st.error(
                f"🚫 Daily limit reached! Maximum {MAX_SESSIONS_PER_DAY} sessions per day."
            )
            return False
        elif sessions_remaining == 1:
            st.info(
                f"ℹ️ You can add {sessions_remaining} more session today ({current_total}/{MAX_SESSIONS_PER_DAY} used)"
            )
        else:
            st.info(
                f"ℹ️ You can add {sessions_remaining} more sessions today ({current_total}/{MAX_SESSIONS_PER_DAY} used)"
            )

        return True

    except Exception as e:
        logger.error(f"Error checking session limits: {str(e)}")
        st.error("❌ Error checking session limits. Please try again.")
        return False


def render_session_form_fields(doctor: Dict, selected_date: date) -> None:
    """
    Render the actual form fields for session entry.

    Args:
        doctor: Doctor information
        selected_date: Selected date
    """
    logger.debug("Rendering session form fields")

    # Create form columns
    col1, col2, col3, col4, col5 = st.columns([1.5, 1.5, 2, 1.5, 1])

    with col1:
        start_time = st.time_input(
            "Start Time:",
            value=None,
            key="start_time_input",
            step=60,
            help="Select start time for the session",
        )

    with col2:
        end_time = st.time_input(
            "End Time:",
            value=None,
            key="end_time_input",
            step=60,
            help="Select end time for the session",
        )

    with col3:
        scribe_name = st.text_input(
            "Scribe Name:", key="scribe_name_input", placeholder="Enter scribe name"
        )

    with col4:
        patient_number = st.number_input(
            "Patient #:",
            min_value=1,
            max_value=999999,
            value=None,
            key="patient_number_input",
            placeholder="Enter patient number",
        )

    with col5:
        add_button = st.button("Add Session", type="primary", use_container_width=True)

    # Handle form submission
    if add_button:
        handle_add_session(
            doctor, selected_date, start_time, end_time, scribe_name, patient_number
        )


def handle_add_session(
    doctor: Dict,
    selected_date: date,
    start_time: Optional[time],
    end_time: Optional[time],
    scribe_name: str,
    patient_number: Optional[int],
) -> None:
    """
    Handle adding a new session with comprehensive validation.

    Args:
        doctor: Doctor information
        selected_date: Selected date
        start_time: Session start time
        end_time: Session end time
        scribe_name: Scribe name
        patient_number: Patient number
    """
    logger.info(f"Handling add session for doctor {doctor['id']}, date {selected_date}")

    try:
        # Validate all fields are filled
        if not validate_form_fields(start_time, end_time, scribe_name, patient_number):
            return

        # Create session dictionary
        new_session = create_session_dict(
            selected_date, start_time, end_time, scribe_name, patient_number
        )

        # Validate session data
        if not validate_new_session(new_session):
            return

        # Check for conflicts
        if not check_session_conflicts(doctor, selected_date, new_session):
            return

        # Check daily limits
        if not validate_daily_limits(doctor, selected_date, new_session):
            return

        # Add to draft sessions
        add_session_to_drafts(new_session)

    except Exception as e:
        logger.error(f"Error handling add session: {str(e)}")
        st.error("❌ An error occurred while adding the session. Please try again.")


def validate_form_fields(
    start_time: Optional[time],
    end_time: Optional[time],
    scribe_name: str,
    patient_number: Optional[int],
) -> bool:
    """
    Validate that all form fields are properly filled.

    Returns:
        True if all fields are valid
    """
    if (
        start_time is None
        or end_time is None
        or not scribe_name
        or scribe_name.strip() == ""
        or patient_number is None
        or patient_number == 0
    ):

        st.error(ERROR_MESSAGES["missing_required_field"])
        logger.warning("Form validation failed - missing required fields")
        return False

    return True


def create_session_dict(
    selected_date: date,
    start_time: time,
    end_time: time,
    scribe_name: str,
    patient_number: int,
) -> Dict[str, Any]:
    """
    Create session dictionary from form inputs.

    Returns:
        Session dictionary
    """
    session = {
        "date": selected_date.strftime("%Y-%m-%d"),
        "start_time": start_time.strftime("%H:%M"),
        "end_time": end_time.strftime("%H:%M"),
        "scribe_name": scribe_name.strip(),
        "patient_number": int(patient_number),
    }

    logger.debug(f"Created session dict: {session}")
    return session


def validate_new_session(session: Dict[str, Any]) -> bool:
    """
    Validate session data using business rules.

    Args:
        session: Session dictionary

    Returns:
        True if session is valid
    """
    is_valid, errors = validate_session_data(session)
    if not is_valid:
        for error in errors:
            st.error(error)
        logger.warning(f"Session validation failed: {errors}")
        return False

    return True


def check_session_conflicts(
    doctor: Dict, selected_date: date, new_session: Dict
) -> bool:
    """
    Check for session time conflicts.

    Args:
        doctor: Doctor information
        selected_date: Selected date
        new_session: New session to check

    Returns:
        True if no conflicts found
    """
    try:
        existing_sessions = get_existing_sessions(
            doctor["id"], selected_date.strftime("%Y-%m-%d")
        )
        all_sessions = existing_sessions + st.session_state.draft_sessions

        has_overlap, conflict_details = check_session_overlap(new_session, all_sessions)
        if has_overlap:
            for conflict in conflict_details:
                st.error(conflict)
            logger.warning(f"Session conflicts detected: {conflict_details}")
            return False

        return True

    except Exception as e:
        logger.error(f"Error checking session conflicts: {str(e)}")
        st.error("❌ Error checking for conflicts. Please try again.")
        return False


def validate_daily_limits(doctor: Dict, selected_date: date, new_session: Dict) -> bool:
    """
    Validate daily session limits.

    Args:
        doctor: Doctor information
        selected_date: Selected date
        new_session: New session to validate

    Returns:
        True if within limits
    """
    try:
        existing_sessions = get_existing_sessions(
            doctor["id"], selected_date.strftime("%Y-%m-%d")
        )
        draft_sessions_with_new = st.session_state.draft_sessions + [new_session]

        within_limit, limit_error = check_daily_session_limit(
            doctor["id"],
            selected_date.strftime("%Y-%m-%d"),
            existing_sessions,
            draft_sessions_with_new,
        )

        if not within_limit:
            st.error(ERROR_MESSAGES["daily_limit_exceeded"])
            st.error(f"Details: {limit_error}")
            logger.warning(f"Daily limit exceeded: {limit_error}")
            return False

        return True

    except Exception as e:
        logger.error(f"Error validating daily limits: {str(e)}")
        st.error("❌ Error checking daily limits. Please try again.")
        return False


def add_session_to_drafts(session: Dict[str, Any]) -> None:
    """
    Add session to draft list and clear form.

    Args:
        session: Session to add to drafts
    """
    logger.info(f"Adding session to drafts: {session}")

    st.session_state.draft_sessions.append(session)
    st.success(SUCCESS_MESSAGES["session_added"])

    # Clear form by removing session state keys
    clear_form_fields()

    logger.info(
        f"Session added to drafts. Total drafts: {len(st.session_state.draft_sessions)}"
    )
    st.rerun()


def clear_form_fields() -> None:
    """Clear form input fields"""
    form_keys = [
        "start_time_input",
        "end_time_input",
        "scribe_name_input",
        "patient_number_input",
    ]

    for key in form_keys:
        if key in st.session_state:
            del st.session_state[key]

    logger.debug("Form fields cleared")


# =============================================================================
# SESSIONS DISPLAY (SIMPLIFIED FOR BREVITY)
# =============================================================================


def render_sessions_list(doctor: Dict, selected_date: date) -> None:
    """Render the sessions list (simplified version)"""
    logger.debug(
        f"Rendering sessions list for doctor {doctor['id']}, date {selected_date}"
    )

    try:
        date_str = selected_date.strftime("%Y-%m-%d")
        date_display = selected_date.strftime("%B %d, %Y")

        # Get existing sessions from Google Sheets
        existing_sessions = get_existing_sessions(doctor["id"], date_str)

        # Combine existing and draft sessions
        all_sessions = existing_sessions + st.session_state.draft_sessions

        if not all_sessions:
            st.info(INFO_MESSAGES["no_sessions"])
            return

        st.subheader(f"📋 Sessions for {date_display}")

        # Simple table display
        for i, session in enumerate(
            sorted(all_sessions, key=lambda x: x["start_time"])
        ):
            with st.container(border=True):
                col1, col2, col3, col4, col5 = st.columns([1.5, 1.5, 2, 1.5, 1.5])

                with col1:
                    st.write(f"**{session['start_time']}**")
                with col2:
                    st.write(f"**{session['end_time']}**")
                with col3:
                    st.write(session["scribe_name"])
                with col4:
                    st.write(f"#{session['patient_number']}")
                with col5:
                    if st.button(
                        "Delete",
                        key=f"delete_{i}",
                        use_container_width=True,
                        type="secondary",
                    ):
                        handle_delete_session(session, i)

                    # Show status
                    if "submission_id" in session:
                        st.markdown(":green[✓ Submitted]")
                    else:
                        st.markdown(":orange[📝 Draft]")

    except Exception as e:
        logger.error(f"Error rendering sessions list: {str(e)}")
        st.error("❌ Error loading sessions. Please refresh the page.")


def handle_delete_session(session: Dict, index: int) -> None:
    """Handle deleting a session"""
    logger.info(f"Handling delete session at index {index}")

    try:
        if "submission_id" in session:
            # Delete from Google Sheets
            success = delete_submission(session["submission_id"])
            if success:
                st.success("✅ Session deleted successfully!")
                st.rerun()
        else:
            # Delete from drafts
            if index < len(st.session_state.draft_sessions):
                del st.session_state.draft_sessions[index]
                st.success("✅ Draft session deleted!")
                st.rerun()

    except Exception as e:
        logger.error(f"Error deleting session: {str(e)}")
        st.error("❌ Error deleting session. Please try again.")


# =============================================================================
# SUBMISSION HANDLING
# =============================================================================


def render_submission_section(doctor: Dict, selected_date: date) -> None:
    """Render the submission section for draft sessions"""
    if not st.session_state.draft_sessions:
        return

    logger.debug(
        f"Rendering submission section with {len(st.session_state.draft_sessions)} draft sessions"
    )

    session_count = len(st.session_state.draft_sessions)
    date_display = selected_date.strftime("%B %d")

    submit_text = f"✅ Submit {session_count} session{'s' if session_count != 1 else ''} for {date_display}"

    if st.button(submit_text, type="primary", use_container_width=True):
        handle_submit_sessions(doctor, selected_date)


def handle_submit_sessions(doctor: Dict, selected_date: date) -> None:
    """Handle submitting all draft sessions to Google Sheets"""
    logger.info(
        f"Handling submit sessions for doctor {doctor['id']}, date {selected_date}"
    )

    try:
        if not st.session_state.draft_sessions:
            st.error(ERROR_MESSAGES["no_sessions_to_submit"])
            return

        # Submit sessions to Google Sheets
        success = save_sessions_to_sheets(
            st.session_state.draft_sessions, doctor, POC_TEAM_LEADER["username"]
        )

        if success:
            session_count = len(st.session_state.draft_sessions)
            success_msg = SUCCESS_MESSAGES["sessions_submitted"].format(
                count=session_count
            )
            st.success(success_msg)

            logger.info(f"Successfully submitted {session_count} sessions")

            # Clear draft sessions
            st.session_state.draft_sessions = []
            st.rerun()
        else:
            st.error(ERROR_MESSAGES["submission_failed"])
            logger.error("Failed to submit sessions to Google Sheets")

    except Exception as e:
        logger.error(f"Error submitting sessions: {str(e)}")
        st.error("❌ Error submitting sessions. Please try again.")


# =============================================================================
# MAIN APPLICATION FLOW
# =============================================================================


def render_main_interface() -> None:
    """Render the main application interface"""
    logger.debug("Rendering main interface")

    try:
        # Header with doctor and date selection
        doctor, selected_date, weekend_override = render_doctor_date_selection()

        if not doctor:
            st.error("Please select a doctor")
            logger.warning("No doctor selected")
            return

        st.markdown("---")

        # Add session form
        render_add_session_form(doctor, selected_date, weekend_override)

        st.markdown("---")

        # Sessions list
        render_sessions_list(doctor, selected_date)

        st.markdown("---")

        # Submission section
        render_submission_section(doctor, selected_date)

        # # Navigation section
        # render_navigation_links()

    except Exception as e:
        logger.error(f"Error rendering main interface: {str(e)}")
        st.error("❌ An error occurred. Please refresh the page.")


def render_navigation_links() -> None:
    """Render navigation links to other pages"""
    st.markdown("---")
    st.subheader("🧭 Other Pages")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("**📊 [View Analytics & Audit](http://localhost:8503)**")
        st.caption("Run: streamlit run src/ui/pages/audit.py --server.port 8504")

    with col2:
        st.markdown("**📤 [Excel Export](http://localhost:8503)**")
        st.caption("Run: streamlit run src/ui/pages/export.py --server.port 8505")


# =============================================================================
# APPLICATION ENTRY POINT
# =============================================================================


def main() -> None:
    """
    Main application entry point with comprehensive error handling.
    """
    logger.info("Starting Medical Schedule Management System")

    try:
        # Setup Streamlit app
        setup_streamlit_app()

        # Initialize session state
        initialize_session_state()

        # Render application header
        render_application_header()

        # Render main interface
        render_main_interface()

        logger.debug("Main application rendering complete")

    except Exception as e:
        logger.critical(f"Critical error in main application: {str(e)}")
        st.error("❌ Critical application error. Please check logs and restart.")

        # Show error details in debug mode
        if is_debug_mode():
            st.exception(e)

        # Stop execution
        st.stop()


# =============================================================================
# STREAMLIT ENTRY POINT
# =============================================================================

if __name__ == "__main__":
    main()
