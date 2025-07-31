# validation.py - Business Rules and Validation for Medical Schedule Management
# Simple functions for validating session data and enforcing business rules

from datetime import datetime, date, time
from typing import List, Dict, Any, Tuple

from config import (
    MIN_SESSION_DURATION_MINUTES,
    MAX_SESSION_DURATION_MINUTES,
    WEEKEND_DAYS,
    SCRIBE_NAME_MIN_LENGTH,
    SCRIBE_NAME_MAX_LENGTH,
    PATIENT_NUMBER_MIN,
    PATIENT_NUMBER_MAX,
    MAX_SESSIONS_PER_DAY,
)


# def validate_session_data(session: Dict) -> Tuple[bool, List[str]]:
#     """
#     Validate a single session's data against business rules.

#     Args:
#         session: Dictionary with session data

#     Returns:
#         Tuple of (is_valid: bool, errors: List[str])
#     """
#     errors = []

#     # Check required fields
#     required_fields = [
#         "date",
#         "start_time",
#         "end_time",
#         "scribe_name",
#         "patient_number",
#     ]
#     for field in required_fields:
#         if field not in session or not str(session[field]).strip():
#             errors.append(f"{field.replace('_', ' ').title()} is required")

#     # If basic fields are missing, return early
#     if errors:
#         return False, errors

#     # Validate date format
#     try:
#         session_date = datetime.strptime(session["date"], "%Y-%m-%d").date()
#     except ValueError:
#         errors.append("Invalid date format. Use YYYY-MM-DD")
#         return False, errors

#     # Validate time format and logic
#     time_valid, time_errors = validate_session_times(
#         session["start_time"], session["end_time"]
#     )
#     if not time_valid:
#         errors.extend(time_errors)

#     # Validate scribe name
#     scribe_name = str(session["scribe_name"]).strip()
#     if len(scribe_name) < SCRIBE_NAME_MIN_LENGTH:
#         errors.append(
#             f"Scribe name must be at least {SCRIBE_NAME_MIN_LENGTH} characters"
#         )
#     elif len(scribe_name) > SCRIBE_NAME_MAX_LENGTH:
#         errors.append(f"Scribe name cannot exceed {SCRIBE_NAME_MAX_LENGTH} characters")

#     # Validate patient number
#     try:
#         patient_num = int(session["patient_number"])
#         if patient_num < PATIENT_NUMBER_MIN or patient_num > PATIENT_NUMBER_MAX:
#             errors.append(
#                 f"Patient number must be between {PATIENT_NUMBER_MIN} and {PATIENT_NUMBER_MAX}"
#             )
#     except (ValueError, TypeError):
#         errors.append("Patient number must be a valid number")

#     return len(errors) == 0, errors


def validate_session_data(session: Dict) -> Tuple[bool, List[str]]:
    """
    Validate a single session's data against business rules.

    Args:
        session: Dictionary with session data

    Returns:
        Tuple of (is_valid: bool, errors: List[str])
    """
    errors = []

    # Check required fields - MORE STRICT CHECKING
    required_fields = [
        "date",
        "start_time",
        "end_time",
        "scribe_name",
        "patient_number",
    ]

    for field in required_fields:
        if field not in session:
            errors.append(f"{field.replace('_', ' ').title()} is required")
        elif field == "patient_number":
            # Special handling for patient number - check if it's empty, None, or 0
            try:
                patient_val = session[field]
                if patient_val is None or patient_val == "" or patient_val == 0:
                    errors.append("Patient number is required and cannot be empty")
            except (ValueError, TypeError):
                errors.append("Patient number is required and cannot be empty")
        elif not str(session[field]).strip():
            # For other fields, check if empty or just whitespace
            errors.append(f"{field.replace('_', ' ').title()} is required")

    # If basic fields are missing, return early
    if errors:
        return False, errors

    # Validate date format
    try:
        session_date = datetime.strptime(session["date"], "%Y-%m-%d").date()
    except ValueError:
        errors.append("Invalid date format. Use YYYY-MM-DD")
        return False, errors

    # Validate time format and logic
    time_valid, time_errors = validate_session_times(
        session["start_time"], session["end_time"]
    )
    if not time_valid:
        errors.extend(time_errors)

    # Validate scribe name
    scribe_name = str(session["scribe_name"]).strip()
    if len(scribe_name) < SCRIBE_NAME_MIN_LENGTH:
        errors.append(
            f"Scribe name must be at least {SCRIBE_NAME_MIN_LENGTH} characters"
        )
    elif len(scribe_name) > SCRIBE_NAME_MAX_LENGTH:
        errors.append(f"Scribe name cannot exceed {SCRIBE_NAME_MAX_LENGTH} characters")

    # Validate patient number - ENHANCED VALIDATION
    try:
        patient_num = int(session["patient_number"])
        if patient_num < PATIENT_NUMBER_MIN or patient_num > PATIENT_NUMBER_MAX:
            errors.append(
                f"Patient number must be between {PATIENT_NUMBER_MIN} and {PATIENT_NUMBER_MAX}"
            )
        elif patient_num == 0:
            errors.append("Patient number cannot be zero")
    except (ValueError, TypeError):
        errors.append("Patient number must be a valid number")

    return len(errors) == 0, errors


def validate_session_times(start_time: str, end_time: str) -> Tuple[bool, List[str]]:
    """
    Validate session start and end times.

    Args:
        start_time: Start time in HH:MM format
        end_time: End time in HH:MM format

    Returns:
        Tuple of (is_valid: bool, errors: List[str])
    """
    errors = []

    try:
        # Parse times
        start = datetime.strptime(start_time, "%H:%M").time()
        end = datetime.strptime(end_time, "%H:%M").time()
    except ValueError:
        errors.append("Invalid time format. Use HH:MM")
        return False, errors

    # Check if end time is after start time
    if start >= end:
        errors.append("End time must be after start time")
        return False, errors

    # Calculate duration
    start_dt = datetime.combine(datetime.today(), start)
    end_dt = datetime.combine(datetime.today(), end)
    duration_minutes = int((end_dt - start_dt).total_seconds() / 60)

    # Validate duration limits
    if duration_minutes < MIN_SESSION_DURATION_MINUTES:
        errors.append(
            f"Session must be at least {MIN_SESSION_DURATION_MINUTES} minutes"
        )

    if duration_minutes > MAX_SESSION_DURATION_MINUTES:
        errors.append(
            f"Session cannot exceed {MAX_SESSION_DURATION_MINUTES} minutes ({MAX_SESSION_DURATION_MINUTES // 60} hours)"
        )

    return len(errors) == 0, errors


def check_session_overlap(
    new_session: Dict, existing_sessions: List[Dict]
) -> Tuple[bool, List[str]]:
    """
    Check if a new session overlaps with existing sessions.

    Args:
        new_session: Dictionary with new session data
        existing_sessions: List of existing session dictionaries

    Returns:
        Tuple of (has_overlap: bool, conflict_details: List[str])
    """
    if not existing_sessions:
        return False, []

    conflicts = []

    try:
        # Parse new session times
        new_start = datetime.strptime(new_session["start_time"], "%H:%M").time()
        new_end = datetime.strptime(new_session["end_time"], "%H:%M").time()
        new_start_mins = new_start.hour * 60 + new_start.minute
        new_end_mins = new_end.hour * 60 + new_end.minute

        for existing in existing_sessions:
            # Skip if checking against the same session (for updates)
            if new_session.get("submission_id") and existing.get(
                "submission_id"
            ) == new_session.get("submission_id"):
                continue

            try:
                # Parse existing session times
                exist_start = datetime.strptime(existing["start_time"], "%H:%M").time()
                exist_end = datetime.strptime(existing["end_time"], "%H:%M").time()
                exist_start_mins = exist_start.hour * 60 + exist_start.minute
                exist_end_mins = exist_end.hour * 60 + exist_end.minute

                # Check for overlap: sessions overlap if one starts before the other ends
                if new_start_mins < exist_end_mins and exist_start_mins < new_end_mins:
                    conflict_detail = (
                        f"Overlaps with existing session {existing['start_time']}-{existing['end_time']} "
                        f"(Scribe: {existing['scribe_name']}, Patient: {existing['patient_number']})"
                    )
                    conflicts.append(conflict_detail)

            except ValueError:
                # Skip malformed existing sessions
                continue

    except ValueError:
        # If new session times are malformed, return error
        return True, ["Invalid time format in new session"]

    return len(conflicts) > 0, conflicts


def check_daily_session_limit(
    doctor_id: str, date: str, existing_sessions: List[Dict], draft_sessions: List[Dict]
) -> Tuple[bool, str]:
    """
    Check if adding sessions would exceed the daily limit.

    Args:
        doctor_id: Doctor ID
        date: Date in YYYY-MM-DD format
        existing_sessions: Already submitted sessions for this date
        draft_sessions: Current draft sessions for this date

    Returns:
        Tuple of (is_within_limit: bool, error_message: str)
    """
    total_sessions = len(existing_sessions) + len(draft_sessions)

    if total_sessions > MAX_SESSIONS_PER_DAY:
        return (
            False,
            f"Cannot exceed {MAX_SESSIONS_PER_DAY} sessions per day. Currently have {len(existing_sessions)} submitted + {len(draft_sessions)} draft = {total_sessions} total",
        )

    return True, ""


def validate_draft_sessions(
    draft_sessions: List[Dict], existing_sessions: List[Dict] = None
) -> Tuple[bool, Dict[int, List[str]]]:
    """
    Validate a list of draft sessions for submission.

    Args:
        draft_sessions: List of session dictionaries to validate
        existing_sessions: List of existing sessions to check against (optional)

    Returns:
        Tuple of (all_valid: bool, session_errors: Dict[index: List[errors]])
    """
    if not draft_sessions:
        return False, {0: ["No sessions to validate"]}

    session_errors = {}
    all_sessions = (existing_sessions or []) + draft_sessions

    for i, session in enumerate(draft_sessions):
        errors = []

        # Validate individual session data
        is_valid, validation_errors = validate_session_data(session)
        if not is_valid:
            errors.extend(validation_errors)

        # Check for overlaps with existing sessions and other draft sessions
        if is_valid:  # Only check overlaps if basic validation passed
            has_overlap, conflict_details = check_session_overlap(
                session, all_sessions[:i] + (existing_sessions or [])
            )
            if has_overlap:
                errors.extend(conflict_details)

        if errors:
            session_errors[i] = errors

    return len(session_errors) == 0, session_errors


def is_weekend(check_date: date) -> bool:
    """
    Check if a date falls on a weekend.

    Args:
        check_date: Date to check

    Returns:
        bool: True if weekend, False otherwise
    """
    return check_date.weekday() in WEEKEND_DAYS


def get_weekend_info(check_date: date) -> Dict[str, Any]:
    """
    Get weekend information for a date.

    Args:
        check_date: Date to check

    Returns:
        Dictionary with weekend information
    """
    is_weekend_day = is_weekend(check_date)

    return {
        "is_weekend": is_weekend_day,
        "day_name": check_date.strftime("%A"),
        "message": (
            f"{check_date.strftime('%A')} is a weekend day"
            if is_weekend_day
            else f"{check_date.strftime('%A')} is a weekday"
        ),
        "requires_override": is_weekend_day,
    }


def validate_date_for_scheduling(
    schedule_date: date,
) -> Tuple[bool, List[str], List[str]]:
    """
    Validate if a date is suitable for scheduling.

    Args:
        schedule_date: Date to validate

    Returns:
        Tuple of (is_valid: bool, errors: List[str], warnings: List[str])
    """
    errors = []
    warnings = []

    # Check if date is in the past (could be configurable)
    today = date.today()
    if schedule_date < today:
        warnings.append(
            f"Scheduling for past date ({schedule_date.strftime('%Y-%m-%d')})"
        )

    # Check if weekend
    if is_weekend(schedule_date):
        warnings.append(
            f"Selected date is a weekend ({schedule_date.strftime('%A')}). Weekend override may be required."
        )

    # Check if date is too far in future (could be configurable)
    days_in_future = (schedule_date - today).days
    if days_in_future > 365:  # More than a year in future
        warnings.append(f"Scheduling very far in future ({days_in_future} days)")

    return len(errors) == 0, errors, warnings


def calculate_total_duration(sessions: List[Dict]) -> Dict[str, Any]:
    """
    Calculate total duration for a list of sessions.

    Args:
        sessions: List of session dictionaries

    Returns:
        Dictionary with duration information
    """
    if not sessions:
        return {
            "total_minutes": 0,
            "total_hours": 0.0,
            "formatted": "0:00",
            "average_session_minutes": 0,
        }

    total_minutes = 0
    valid_sessions = 0

    for session in sessions:
        try:
            start = datetime.strptime(session["start_time"], "%H:%M").time()
            end = datetime.strptime(session["end_time"], "%H:%M").time()

            start_dt = datetime.combine(datetime.today(), start)
            end_dt = datetime.combine(datetime.today(), end)

            if end_dt > start_dt:  # Valid time range
                duration = int((end_dt - start_dt).total_seconds() / 60)
                total_minutes += duration
                valid_sessions += 1

        except ValueError:
            # Skip sessions with invalid time format
            continue

    total_hours = total_minutes / 60.0
    hours = total_minutes // 60
    minutes = total_minutes % 60
    formatted = f"{hours}:{minutes:02d}"

    average_minutes = total_minutes // valid_sessions if valid_sessions > 0 else 0

    return {
        "total_minutes": total_minutes,
        "total_hours": round(total_hours, 2),
        "formatted": formatted,
        "average_session_minutes": average_minutes,
        "valid_sessions": valid_sessions,
    }


def get_time_conflicts_summary(sessions: List[Dict]) -> Dict[str, Any]:
    """
    Analyze sessions for any time conflicts.

    Args:
        sessions: List of session dictionaries

    Returns:
        Dictionary with conflict analysis
    """
    conflicts = []

    for i, session1 in enumerate(sessions):
        for j, session2 in enumerate(sessions[i + 1 :], i + 1):
            has_overlap, conflict_details = check_session_overlap(session1, [session2])
            if has_overlap:
                conflicts.append(
                    {
                        "session1_index": i,
                        "session2_index": j,
                        "session1_time": f"{session1['start_time']}-{session1['end_time']}",
                        "session2_time": f"{session2['start_time']}-{session2['end_time']}",
                        "details": (
                            conflict_details[0]
                            if conflict_details
                            else "Time overlap detected"
                        ),
                    }
                )

    return {
        "has_conflicts": len(conflicts) > 0,
        "conflict_count": len(conflicts),
        "conflicts": conflicts,
    }


def validate_submission_readiness(
    doctor_id: str,
    date: str,
    draft_sessions: List[Dict],
    existing_sessions: List[Dict] = None,
) -> Dict[str, Any]:
    """
    Comprehensive validation before allowing submission.

    Args:
        doctor_id: Doctor ID
        date: Date string
        draft_sessions: Sessions to be submitted
        existing_sessions: Existing sessions for the date

    Returns:
        Dictionary with submission readiness assessment
    """
    errors = []
    warnings = []

    # Check if there are sessions to submit
    if not draft_sessions:
        errors.append("No sessions to submit")

    # Daily session limit validation
    if existing_sessions is None:
        existing_sessions = []

    within_limit, limit_error = check_daily_session_limit(
        doctor_id, date, existing_sessions, draft_sessions
    )
    if not within_limit:
        errors.append(limit_error)

    # Validate each session
    if draft_sessions:
        all_valid, session_errors = validate_draft_sessions(
            draft_sessions, existing_sessions
        )
        if not all_valid:
            for session_idx, session_errs in session_errors.items():
                errors.extend(
                    [f"Session {session_idx + 1}: {err}" for err in session_errs]
                )

    # Check date validity
    try:
        schedule_date = datetime.strptime(date, "%Y-%m-%d").date()
        date_valid, date_errors, date_warnings = validate_date_for_scheduling(
            schedule_date
        )
        errors.extend(date_errors)
        warnings.extend(date_warnings)
    except ValueError:
        errors.append("Invalid date format")

    # Analyze conflicts
    all_sessions = (existing_sessions or []) + draft_sessions
    conflict_analysis = get_time_conflicts_summary(all_sessions)
    if conflict_analysis["has_conflicts"]:
        for conflict in conflict_analysis["conflicts"]:
            errors.append(f"Time conflict: {conflict['details']}")

    # Calculate duration summary
    duration_info = calculate_total_duration(draft_sessions)

    return {
        "ready_for_submission": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
        "session_count": len(draft_sessions),
        "duration_info": duration_info,
        "conflict_analysis": conflict_analysis,
    }
