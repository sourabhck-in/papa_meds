# main.py - Simple Medical Schedule Management System
# Clean, single-page interface focused on core scheduling workflow

import streamlit as st
import pandas as pd
from datetime import datetime, date, time

# Import our modules
from config import (
    APP_TITLE,
    APP_ICON,
    POC_TEAM_LEADER,
    POC_DOCTORS,
    LABELS,
    SUCCESS_MESSAGES,
    ERROR_MESSAGES,
    INFO_MESSAGES,
    MAX_SESSIONS_PER_DAY,
)
from data_ops import (
    load_submissions,
    save_sessions_to_csv,
    get_existing_sessions,
    get_day_summary,
    format_doctor_name,
    update_submission,
    delete_submission,
)
from validation import (
    validate_session_data,
    check_session_overlap,
    validate_draft_sessions,
    is_weekend,
    get_weekend_info,
    validate_submission_readiness,
    check_daily_session_limit,
)

# =============================================================================
# APP CONFIGURATION AND INITIALIZATION
# =============================================================================


def setup_app():
    """Configure Streamlit app"""
    st.set_page_config(
        page_title="Medical Schedule Manager",
        page_icon=APP_ICON,
        layout="wide",
        initial_sidebar_state="collapsed",
    )


def initialize_session_state():
    """Initialize session state variables"""
    if "draft_sessions" not in st.session_state:
        st.session_state.draft_sessions = []
    if "selected_doctor" not in st.session_state:
        st.session_state.selected_doctor = None
    if "selected_date" not in st.session_state:
        st.session_state.selected_date = date.today()


# =============================================================================
# DOCTOR AND DATE SELECTION
# =============================================================================


def render_header_selection():
    """Render doctor and date selection header"""
    st.title(f"{APP_ICON} {APP_TITLE}")

    # Create columns for selections
    col1, col2, col3 = st.columns([2, 2, 1])

    with col1:
        # Doctor selection
        doctor_options = [format_doctor_name(doc) for doc in POC_DOCTORS]
        selected_doctor_name = st.selectbox(
            LABELS["doctor_selection"], options=doctor_options, key="doctor_selector"
        )

        # Find selected doctor info
        selected_doctor = None
        for doc in POC_DOCTORS:
            if format_doctor_name(doc) == selected_doctor_name:
                selected_doctor = doc
                break

        st.session_state.selected_doctor = selected_doctor

    with col2:
        # Check if we have draft sessions
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

            # Show clear warning and action needed
            st.warning(
                f"⚠️ You have {len(st.session_state.draft_sessions)} unsaved draft session(s)"
            )
            st.info(
                "💡 Please **Submit** your sessions or **Delete** them to change the date"
            )

            # Optional: Add a "Clear All Drafts" button for emergency cases
            if st.button(
                "🗑️ Clear All Draft Sessions", type="secondary", use_container_width=True
            ):
                st.session_state.draft_sessions = []
                st.success("All draft sessions cleared! You can now change the date.")
                st.rerun()

        else:
            # Normal date selection when no drafts
            selected_date = st.date_input(
                LABELS["date_selection"],
                value=st.session_state.selected_date,
                key="date_selector",
            )
            st.session_state.selected_date = selected_date

        # Use the stored selected date
        selected_date = st.session_state.selected_date

        # Weekend info
        weekend_info = get_weekend_info(selected_date)
        if weekend_info["is_weekend"]:
            st.info(f"🏖️ {weekend_info['day_name']} is a weekend")

    with col3:
        # Weekend override if needed
        weekend_override = False
        if is_weekend(selected_date):
            weekend_override = st.checkbox(
                "Override Weekend", help="Allow scheduling on weekends"
            )

    return selected_doctor, selected_date, weekend_override


# =============================================================================
# SESSION ENTRY FORM
# =============================================================================


# def render_add_session_form(doctor, selected_date, weekend_override):
#     """Render the add session form"""
#     # Check if we can add sessions
#     can_add = True
#     if is_weekend(selected_date) and not weekend_override:
#         can_add = False
#         st.warning(INFO_MESSAGES["weekend_default"])

#     if not can_add:
#         return

#     st.subheader("➕ Add Session")

#     # ADD THIS - Show session count info
#     existing_sessions = get_existing_sessions(
#         doctor["id"], selected_date.strftime("%Y-%m-%d")
#     )
#     current_total = len(existing_sessions) + len(st.session_state.draft_sessions)
#     sessions_remaining = MAX_SESSIONS_PER_DAY - current_total

#     if sessions_remaining <= 0:
#         st.error(
#             f"🚫 Daily limit reached! Maximum {MAX_SESSIONS_PER_DAY} sessions per day."
#         )
#         return
#     elif sessions_remaining == 1:
#         st.info(
#             f"ℹ️ You can add {sessions_remaining} more session today ({current_total}/{MAX_SESSIONS_PER_DAY} used)"
#         )
#     else:
#         st.info(
#             f"ℹ️ You can add {sessions_remaining} more sessions today ({current_total}/{MAX_SESSIONS_PER_DAY} used)"
#         )

#     with st.container(border=True):
#         # Create form columns
#         col1, col2, col3, col4, col5 = st.columns([1.5, 1.5, 2, 1.5, 1])

#         with col1:
#             start_time = st.time_input(
#                 "Start Time:", value=time(9, 0), key="start_time_input", step=60
#             )

#         with col2:
#             end_time = st.time_input(
#                 "End Time:", value=time(17, 0), key="end_time_input", step=60
#             )

#         with col3:
#             scribe_name = st.text_input(
#                 "Scribe Name:", key="scribe_name_input", placeholder="Enter scribe name"
#             )

#         with col4:
#             patient_number = st.number_input(
#                 "Patient #:",
#                 min_value=1,
#                 max_value=999999,
#                 value=1,
#                 key="patient_number_input",
#             )

#         with col5:
#             add_button = st.button(
#                 "Add Session", type="primary", use_container_width=True
#             )

#         # Handle add session
#         if add_button:
#             add_session_to_draft(
#                 doctor, selected_date, start_time, end_time, scribe_name, patient_number
#             )


# def add_session_to_draft(
#     doctor, selected_date, start_time, end_time, scribe_name, patient_number
# ):
#     """Add a session to the draft list"""
#     # Create session dictionary
#     new_session = {
#         "date": selected_date.strftime("%Y-%m-%d"),
#         "start_time": start_time.strftime("%H:%M"),
#         "end_time": end_time.strftime("%H:%M"),
#         "scribe_name": scribe_name.strip(),
#         "patient_number": int(patient_number),
#     }

#     # Validate the session
#     is_valid, errors = validate_session_data(new_session)
#     if not is_valid:
#         for error in errors:
#             st.error(error)
#         return

#     # Check for overlaps with existing sessions and current drafts
#     existing_sessions = get_existing_sessions(
#         doctor["id"], selected_date.strftime("%Y-%m-%d")
#     )
#     all_sessions = existing_sessions + st.session_state.draft_sessions

#     has_overlap, conflict_details = check_session_overlap(new_session, all_sessions)
#     if has_overlap:
#         for conflict in conflict_details:
#             st.error(conflict)
#         return

#     # Daily session limit
#     within_limit, limit_error = check_daily_session_limit(
#         doctor["id"],
#         selected_date.strftime("%Y-%m-%d"),
#         existing_sessions,
#         # Include the new session
#         st.session_state.draft_sessions + [new_session],
#     )
#     if not within_limit:
#         st.error(ERROR_MESSAGES["daily_limit_exceeded"])
#         st.error(f"Details: {limit_error}")
#         return

#     # Add to draft sessions
#     st.session_state.draft_sessions.append(new_session)
#     st.success(SUCCESS_MESSAGES["session_added"])

#     # Clear form by rerunning
#     st.rerun()


def render_add_session_form(doctor, selected_date, weekend_override):
    """Render the add session form"""
    # Check if we can add sessions
    can_add = True
    if is_weekend(selected_date) and not weekend_override:
        can_add = False
        st.warning(INFO_MESSAGES["weekend_default"])

    if not can_add:
        return

    st.subheader("➕ Add Session")

    # Show session count info (daily limit)
    existing_sessions = get_existing_sessions(
        doctor["id"], selected_date.strftime("%Y-%m-%d")
    )
    current_total = len(existing_sessions) + len(st.session_state.draft_sessions)
    sessions_remaining = MAX_SESSIONS_PER_DAY - current_total

    if sessions_remaining <= 0:
        st.error(
            f"🚫 Daily limit reached! Maximum {MAX_SESSIONS_PER_DAY} sessions per day."
        )
        return
    elif sessions_remaining == 1:
        st.info(
            f"ℹ️ You can add {sessions_remaining} more session today ({current_total}/{MAX_SESSIONS_PER_DAY} used)"
        )
    else:
        st.info(
            f"ℹ️ You can add {sessions_remaining} more sessions today ({current_total}/{MAX_SESSIONS_PER_DAY} used)"
        )

    with st.container(border=True):
        # Create form columns
        col1, col2, col3, col4, col5 = st.columns([1.5, 1.5, 2, 1.5, 1])

        with col1:
            # CHANGED: Remove default value, add placeholder
            start_time = st.time_input(
                "Start Time:",
                value=None,  # No default value
                key="start_time_input",
                step=60,
                help="Select start time for the session",
            )

        with col2:
            # CHANGED: Remove default value, add placeholder
            end_time = st.time_input(
                "End Time:",
                value=None,  # No default value
                key="end_time_input",
                step=60,
                help="Select end time for the session",
            )

        with col3:
            # This was already good - no default value
            scribe_name = st.text_input(
                "Scribe Name:", key="scribe_name_input", placeholder="Enter scribe name"
            )

        with col4:
            # CHANGED: Remove default value, add placeholder
            patient_number = st.number_input(
                "Patient #:",
                min_value=1,
                max_value=999999,
                value=None,  # No default value
                key="patient_number_input",
                placeholder="Enter patient number",
            )

        with col5:
            add_button = st.button(
                "Add Session", type="primary", use_container_width=True
            )

        # Handle add session
        if add_button:
            add_session_to_draft(
                doctor, selected_date, start_time, end_time, scribe_name, patient_number
            )


def add_session_to_draft(
    doctor, selected_date, start_time, end_time, scribe_name, patient_number
):
    """Add a session to the draft list"""

    # Check if all fields are filled before proceeding
    if (
        start_time is None
        or end_time is None
        or not scribe_name
        or scribe_name.strip() == ""
        or patient_number is None
        or patient_number == 0
    ):
        st.error(ERROR_MESSAGES["missing_required_field"])
        return

    # Create session dictionary
    new_session = {
        "date": selected_date.strftime("%Y-%m-%d"),
        "start_time": start_time.strftime("%H:%M"),
        "end_time": end_time.strftime("%H:%M"),
        "scribe_name": scribe_name.strip(),
        "patient_number": int(patient_number),
    }

    # Validate the session
    is_valid, errors = validate_session_data(new_session)
    if not is_valid:
        for error in errors:
            st.error(error)
        return

    # Check for overlaps with existing sessions and current drafts
    existing_sessions = get_existing_sessions(
        doctor["id"], selected_date.strftime("%Y-%m-%d")
    )
    all_sessions = existing_sessions + st.session_state.draft_sessions

    has_overlap, conflict_details = check_session_overlap(new_session, all_sessions)
    if has_overlap:
        for conflict in conflict_details:
            st.error(conflict)
        return

    # Check daily session limit
    within_limit, limit_error = check_daily_session_limit(
        doctor["id"],
        selected_date.strftime("%Y-%m-%d"),
        existing_sessions,
        st.session_state.draft_sessions + [new_session],
    )
    if not within_limit:
        st.error(ERROR_MESSAGES["daily_limit_exceeded"])
        st.error(f"Details: {limit_error}")
        return

    # Add to draft sessions
    st.session_state.draft_sessions.append(new_session)
    st.success(SUCCESS_MESSAGES["session_added"])

    # ENHANCED: Clear form by clearing session state keys and rerunning
    # This ensures the form is completely reset
    if "start_time_input" in st.session_state:
        del st.session_state["start_time_input"]
    if "end_time_input" in st.session_state:
        del st.session_state["end_time_input"]
    if "scribe_name_input" in st.session_state:
        del st.session_state["scribe_name_input"]
    if "patient_number_input" in st.session_state:
        del st.session_state["patient_number_input"]

    st.rerun()


# =============================================================================
# SESSIONS DISPLAY
# =============================================================================


def render_sessions_list(doctor, selected_date):
    """Render the list of sessions for the selected date"""
    date_str = selected_date.strftime("%Y-%m-%d")
    date_display = selected_date.strftime("%B %d, %Y")

    # Get existing sessions from CSV
    existing_sessions = get_existing_sessions(doctor["id"], date_str)

    # Combine existing and draft sessions
    all_sessions = existing_sessions + st.session_state.draft_sessions

    if not all_sessions:
        st.info(INFO_MESSAGES["no_sessions"])
        return

    st.subheader(f"📋 Sessions for {date_display}")

    with st.container(border=True):
        # Sort all sessions by start time
        sorted_sessions = sorted(all_sessions, key=lambda x: x["start_time"])

        # Header row
        col1, col2, col3, col4, col5 = st.columns([1.5, 1.5, 2, 1.5, 1.5])
        with col1:
            st.write("**Start Time**")
        with col2:
            st.write("**End Time**")
        with col3:
            st.write("**Scribe Name**")
        with col4:
            st.write("**Patient #**")
        with col5:
            st.write("**Actions**")

        total_minutes = 0

        for i, session in enumerate(sorted_sessions):

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
                    # Only show delete button (wider now)
                    if st.button(
                        "Delete",
                        key=f"delete_{i}",
                        use_container_width=True,
                        type="secondary",
                    ):
                        if "submission_id" in session:
                            delete_submitted_session(session["submission_id"])
                        else:
                            delete_draft_session(i)

                    # Show submission status below button
                    if "submission_id" in session:
                        submitted_date = session.get("submitted_time", "")
                        if submitted_date:
                            try:
                                submit_dt = datetime.strptime(
                                    submitted_date, "%Y-%m-%d %H:%M:%S"
                                )
                                submit_date_str = submit_dt.strftime("%b %d")
                                st.markdown(
                                    f""":green[✓ Submitted {submit_date_str}]"""
                                )
                            except:
                                st.caption("✓ Submitted")
                        else:
                            st.caption("✓ Submitted")
                    else:
                        # Show draft indicator
                        st.markdown(":orange[📝 Draft - Please Submit]")

            # Calculate duration for total
            try:
                start = datetime.strptime(session["start_time"], "%H:%M")
                end = datetime.strptime(session["end_time"], "%H:%M")
                duration = (end - start).total_seconds() / 60
                total_minutes += duration
            except:
                pass

        # Show total hours
        total_hours = total_minutes / 60
        st.markdown("---")
        st.write(f"**Total: {total_hours:.1f} hours**")


# =============================================================================
# EDIT FUNCTIONS - COMMENTED OUT (NO LONGER USED)
# =============================================================================

# def render_edit_submitted_session_form():
#     """Render edit form for submitted sessions"""
#     session = st.session_state["editing_submitted_session"]

#     st.subheader("✏️ Edit Submitted Session")

#     with st.container(border=True):
#         # Create form columns
#         col1, col2, col3, col4, col5, col6 = st.columns([1.5, 1.5, 2, 1.5, 1, 1])

#         with col1:
#             start_time = st.time_input(
#                 "Start Time:",
#                 value=datetime.strptime(session["start_time"], "%H:%M").time(),
#                 key="edit_start_time",
#                 step=60,
#             )

#         with col2:
#             end_time = st.time_input(
#                 "End Time:",
#                 value=datetime.strptime(session["end_time"], "%H:%M").time(),
#                 key="edit_end_time",
#                 step=60,
#             )

#         with col3:
#             scribe_name = st.text_input(
#                 "Scribe Name:", value=session["scribe_name"], key="edit_scribe_name"
#             )

#         with col4:
#             patient_number = st.number_input(
#                 "Patient #:",
#                 min_value=1,
#                 max_value=999999,
#                 value=int(session["patient_number"]),
#                 key="edit_patient_number",
#             )

#         with col5:
#             if st.button("Save", type="primary", use_container_width=True):
#                 save_edited_session(
#                     session["submission_id"],
#                     start_time,
#                     end_time,
#                     scribe_name,
#                     patient_number,
#                 )

#         with col6:
#             if st.button("Cancel", use_container_width=True):
#                 del st.session_state["editing_submitted_session"]
#                 st.rerun()


# def save_edited_session(
#     submission_id, start_time, end_time, scribe_name, patient_number
# ):
#     """Save changes to a submitted session"""
#     # Create updated data
#     updated_data = {
#         "start_time": start_time.strftime("%H:%M"),
#         "end_time": end_time.strftime("%H:%M"),
#         "scribe_name": scribe_name.strip(),
#         "patient_number": int(patient_number),
#     }

#     # Validate the updated session
#     is_valid, errors = validate_session_data(
#         {"date": st.session_state.selected_date.strftime("%Y-%m-%d"), **updated_data}
#     )

#     if not is_valid:
#         for error in errors:
#             st.error(error)
#         return

#     # Check for overlaps (excluding this session)
#     doctor = st.session_state.selected_doctor
#     date_str = st.session_state.selected_date.strftime("%Y-%m-%d")
#     existing_sessions = get_existing_sessions(doctor["id"], date_str)

#     # Create temporary session for overlap check
#     temp_session = {"submission_id": submission_id, **updated_data, "date": date_str}

#     has_overlap, conflict_details = check_session_overlap(
#         temp_session, existing_sessions + st.session_state.draft_sessions
#     )
#     if has_overlap:
#         for conflict in conflict_details:
#             st.error(conflict)
#         return

#     # Update the session
#     success = update_submission(submission_id, updated_data)

#     if success:
#         st.success("✅ Session updated successfully!")
#         del st.session_state["editing_submitted_session"]
#         st.rerun()
#     else:
#         st.error("❌ Failed to update session. Please try again.")


# def edit_draft_session(session_index):
#     """Edit a draft session"""
#     if session_index < len(st.session_state.draft_sessions):
#         session = st.session_state.draft_sessions[session_index]

#         # Store the session being edited
#         st.session_state[f"editing_session_{session_index}"] = True
#         st.rerun()


# def edit_submitted_session(session):
#     """Edit a submitted session"""
#     st.session_state["editing_submitted_session"] = session
#     st.rerun()


# =============================================================================
# DELETE FUNCTIONS
# =============================================================================


def delete_draft_session(session_index):
    """Delete a draft session"""
    if session_index < len(st.session_state.draft_sessions):
        del st.session_state.draft_sessions[session_index]
        st.success(SUCCESS_MESSAGES["session_deleted"])
        st.rerun()


def delete_submitted_session(submission_id):
    """Delete a submitted session"""
    success = delete_submission(submission_id)
    if success:
        st.success("✅ Submitted session deleted successfully!")
        st.rerun()
    else:
        st.error("❌ Failed to delete session. Please try again.")


# =============================================================================
# SUBMISSION
# =============================================================================


def render_submission_section(doctor, selected_date):
    """Render the submission section"""
    if not st.session_state.draft_sessions:
        return

    session_count = len(st.session_state.draft_sessions)
    date_display = selected_date.strftime("%B %d")

    # Show submission button
    submit_text = f"✅ Submit {session_count} session{'s' if session_count != 1 else ''} for {date_display}"

    if st.button(submit_text, type="primary", use_container_width=True):
        submit_sessions(doctor, selected_date)


def submit_sessions(doctor, selected_date):
    """Submit all draft sessions"""
    if not st.session_state.draft_sessions:
        st.error(ERROR_MESSAGES["no_sessions_to_submit"])
        return

    # Validate all draft sessions
    date_str = selected_date.strftime("%Y-%m-%d")
    existing_sessions = get_existing_sessions(doctor["id"], date_str)

    readiness = validate_submission_readiness(
        doctor["id"], date_str, st.session_state.draft_sessions, existing_sessions
    )

    if not readiness["ready_for_submission"]:
        st.error("Cannot submit sessions:")
        for error in readiness["errors"]:
            st.error(f"• {error}")
        return

    # Submit sessions
    success = save_sessions_to_csv(
        st.session_state.draft_sessions, doctor, POC_TEAM_LEADER["username"]
    )

    if success:
        session_count = len(st.session_state.draft_sessions)
        success_msg = SUCCESS_MESSAGES["sessions_submitted"].format(count=session_count)
        st.success(success_msg)

        # Clear draft sessions
        st.session_state.draft_sessions = []
        st.rerun()
    else:
        st.error(ERROR_MESSAGES["submission_failed"])


# =============================================================================
# MAIN APPLICATION
# =============================================================================


def main():
    """Main application entry point"""
    setup_app()
    initialize_session_state()

    # Header with doctor and date selection
    doctor, selected_date, weekend_override = render_header_selection()

    if not doctor:
        st.error("Please select a doctor")
        return

    st.markdown("---")

    # Add session form
    render_add_session_form(doctor, selected_date, weekend_override)

    # REMOVED: Edit submitted session form (no longer used)
    # if "editing_submitted_session" in st.session_state:
    #     render_edit_submitted_session_form()

    st.markdown("---")

    # Sessions list
    render_sessions_list(doctor, selected_date)

    st.markdown("---")

    # Submission section
    render_submission_section(doctor, selected_date)

    # Debug info in sidebar (optional)
    if st.sidebar.checkbox("🔧 Debug Info"):
        st.sidebar.subheader("Debug Information")
        st.sidebar.json(
            {
                "selected_doctor": doctor["id"] if doctor else None,
                "selected_date": str(selected_date),
                "draft_sessions_count": len(st.session_state.draft_sessions),
                "weekend_override": (
                    weekend_override if is_weekend(selected_date) else "N/A"
                ),
            }
        )

        if st.session_state.draft_sessions:
            st.sidebar.subheader("Draft Sessions")
            st.sidebar.json(st.session_state.draft_sessions)


if __name__ == "__main__":
    main()
