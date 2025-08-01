# src/core/validators/validation.py
"""
Business Rules and Validation for Medical Schedule Management
Simple functions for validating session data and enforcing business rules
"""

import logging
from datetime import datetime, date, time
from typing import List, Dict, Any, Tuple

# Import from our new config structure
from src.utils.config import (
    MIN_SESSION_DURATION_MINUTES,
    MAX_SESSION_DURATION_MINUTES,
    WEEKEND_DAYS,
    SCRIBE_NAME_MIN_LENGTH,
    SCRIBE_NAME_MAX_LENGTH,
    PATIENT_NUMBER_MIN,
    PATIENT_NUMBER_MAX,
    MAX_SESSIONS_PER_DAY,
)
from src.utils.logging_config import get_logger

# Initialize logger
logger = get_logger(__name__)


def validate_session_data(session: Dict) -> Tuple[bool, List[str]]:
    """
    Validate session data according to business rules.

    Args:
        session: Session dictionary to validate

    Returns:
        Tuple of (is_valid, list_of_errors)
    """
    logger.info("Validating session data: %s", session)
    errors = []

    required_fields = [
        "date",
        "start_time",
        "end_time",
        "scribe_name",
        "patient_number",
    ]

    # Check required fields
    for field in required_fields:
        if field not in session:
            logger.warning("Missing required field: %s", field)
            errors.append(f"{field.replace('_', ' ').title()} is required")
        elif field == "patient_number":
            try:
                patient_val = session[field]
                if patient_val is None or patient_val == "" or patient_val == 0:
                    logger.warning("Patient number is empty or zero")
                    errors.append("Patient number is required and cannot be empty")
            except (ValueError, TypeError):
                logger.warning("Patient number is invalid type")
                errors.append("Patient number is required and cannot be empty")
        elif not str(session[field]).strip():
            logger.warning("Field '%s' is empty or whitespace", field)
            errors.append(f"{field.replace('_', ' ').title()} is required")

    if errors:
        logger.info("Validation failed due to missing fields: %s", errors)
        return False, errors

    # Validate date format
    try:
        session_date = datetime.strptime(session["date"], "%Y-%m-%d").date()
    except ValueError:
        logger.error("Invalid date format: %s", session.get("date"))
        errors.append("Invalid date format. Use YYYY-MM-DD")
        return False, errors

    # Validate session times
    time_valid, time_errors = validate_session_times(
        session["start_time"], session["end_time"]
    )
    if not time_valid:
        logger.info("Session time validation failed: %s", time_errors)
        errors.extend(time_errors)

    # Validate scribe name
    scribe_name = str(session["scribe_name"]).strip()
    if len(scribe_name) < SCRIBE_NAME_MIN_LENGTH:
        logger.warning("Scribe name too short: %s", scribe_name)
        errors.append(
            f"Scribe name must be at least {SCRIBE_NAME_MIN_LENGTH} characters"
        )
    elif len(scribe_name) > SCRIBE_NAME_MAX_LENGTH:
        logger.warning("Scribe name too long: %s", scribe_name)
        errors.append(f"Scribe name cannot exceed {SCRIBE_NAME_MAX_LENGTH} characters")

    # Validate patient number
    try:
        patient_num = int(session["patient_number"])
        if patient_num < PATIENT_NUMBER_MIN or patient_num > PATIENT_NUMBER_MAX:
            logger.warning("Patient number out of range: %s", patient_num)
            errors.append(
                f"Patient number must be between {PATIENT_NUMBER_MIN} and {PATIENT_NUMBER_MAX}"
            )
        elif patient_num == 0:
            logger.warning("Patient number is zero")
            errors.append("Patient number cannot be zero")
    except (ValueError, TypeError):
        logger.error(
            "Patient number is not a valid number: %s", session.get("patient_number")
        )
        errors.append("Patient number must be a valid number")

    logger.info(
        "Session validation result: %s", "Valid" if len(errors) == 0 else errors
    )
    return len(errors) == 0, errors


def validate_session_times(start_time: str, end_time: str) -> Tuple[bool, List[str]]:
    """
    Validate session start and end times.

    Args:
        start_time: Start time in HH:MM format
        end_time: End time in HH:MM format

    Returns:
        Tuple of (is_valid, list_of_errors)
    """
    logger.info("Validating session times: start=%s, end=%s", start_time, end_time)
    errors = []

    try:
        start = datetime.strptime(start_time, "%H:%M").time()
        end = datetime.strptime(end_time, "%H:%M").time()
    except ValueError:
        logger.error("Invalid time format: start=%s, end=%s", start_time, end_time)
        errors.append("Invalid time format. Use HH:MM")
        return False, errors

    if start >= end:
        logger.warning("End time is not after start time: start=%s, end=%s", start, end)
        errors.append("End time must be after start time")
        return False, errors

    # Calculate duration
    start_dt = datetime.combine(datetime.today(), start)
    end_dt = datetime.combine(datetime.today(), end)
    duration_minutes = int((end_dt - start_dt).total_seconds() / 60)

    if duration_minutes < MIN_SESSION_DURATION_MINUTES:
        logger.warning("Session duration too short: %d minutes", duration_minutes)
        errors.append(
            f"Session must be at least {MIN_SESSION_DURATION_MINUTES} minutes"
        )

    if duration_minutes > MAX_SESSION_DURATION_MINUTES:
        logger.warning("Session duration too long: %d minutes", duration_minutes)
        errors.append(
            f"Session cannot exceed {MAX_SESSION_DURATION_MINUTES} minutes ({MAX_SESSION_DURATION_MINUTES // 60} hours)"
        )

    logger.info(
        "Session time validation result: %s", "Valid" if len(errors) == 0 else errors
    )
    return len(errors) == 0, errors


def check_session_overlap(
    new_session: Dict, existing_sessions: List[Dict]
) -> Tuple[bool, List[str]]:
    """
    Check if new session overlaps with existing sessions.

    Args:
        new_session: New session to check
        existing_sessions: List of existing sessions

    Returns:
        Tuple of (has_overlap, list_of_conflicts)
    """
    logger.info("Checking session overlap for new session: %s", new_session)

    if not existing_sessions:
        logger.info("No existing sessions to check for overlap.")
        return False, []

    conflicts = []

    try:
        new_start = datetime.strptime(new_session["start_time"], "%H:%M").time()
        new_end = datetime.strptime(new_session["end_time"], "%H:%M").time()
        new_start_mins = new_start.hour * 60 + new_start.minute
        new_end_mins = new_end.hour * 60 + new_end.minute

        for existing in existing_sessions:
            # Skip if comparing session to itself
            if new_session.get("submission_id") and existing.get(
                "submission_id"
            ) == new_session.get("submission_id"):
                continue

            try:
                exist_start = datetime.strptime(existing["start_time"], "%H:%M").time()
                exist_end = datetime.strptime(existing["end_time"], "%H:%M").time()
                exist_start_mins = exist_start.hour * 60 + exist_start.minute
                exist_end_mins = exist_end.hour * 60 + exist_end.minute

                # Check for overlap
                if new_start_mins < exist_end_mins and exist_start_mins < new_end_mins:
                    conflict_detail = (
                        f"Overlaps with existing session {existing['start_time']}-{existing['end_time']} "
                        f"(Scribe: {existing['scribe_name']}, Patient: {existing['patient_number']})"
                    )
                    logger.warning("Session overlap detected: %s", conflict_detail)
                    conflicts.append(conflict_detail)

            except ValueError:
                logger.error("Malformed time in existing session: %s", existing)
                continue

    except ValueError:
        logger.error("Malformed time in new session: %s", new_session)
        return True, ["Invalid time format in new session"]

    logger.info(
        "Session overlap check result: %s",
        "Conflicts found" if len(conflicts) > 0 else "No conflicts",
    )
    return len(conflicts) > 0, conflicts


def check_daily_session_limit(
    doctor_id: str, date: str, existing_sessions: List[Dict], draft_sessions: List[Dict]
) -> Tuple[bool, str]:
    """
    Check if daily session limit is exceeded.

    Args:
        doctor_id: Doctor ID
        date: Date string
        existing_sessions: List of existing sessions
        draft_sessions: List of draft sessions

    Returns:
        Tuple of (within_limit, error_message)
    """
    logger.info(
        "Checking daily session limit for doctor_id=%s, date=%s", doctor_id, date
    )
    total_sessions = len(existing_sessions) + len(draft_sessions)

    if total_sessions > MAX_SESSIONS_PER_DAY:
        logger.warning("Daily session limit exceeded: %d sessions", total_sessions)
        return (
            False,
            f"Cannot exceed {MAX_SESSIONS_PER_DAY} sessions per day. Currently have {len(existing_sessions)} submitted + {len(draft_sessions)} draft = {total_sessions} total",
        )

    logger.info("Daily session limit check passed: %d sessions", total_sessions)
    return True, ""


def validate_draft_sessions(
    draft_sessions: List[Dict], existing_sessions: List[Dict] = None
) -> Tuple[bool, Dict[int, List[str]]]:
    """
    Validate all draft sessions.

    Args:
        draft_sessions: List of draft sessions to validate
        existing_sessions: List of existing sessions for conflict checking

    Returns:
        Tuple of (all_valid, dict_of_session_errors)
    """
    logger.info(
        "Validating draft sessions: %d sessions",
        len(draft_sessions) if draft_sessions else 0,
    )

    if not draft_sessions:
        logger.warning("No draft sessions to validate.")
        return False, {0: ["No sessions to validate"]}

    session_errors = {}
    all_sessions = (existing_sessions or []) + draft_sessions

    for i, session in enumerate(draft_sessions):
        logger.info("Validating draft session #%d: %s", i + 1, session)
        errors = []

        # Validate session data
        is_valid, validation_errors = validate_session_data(session)
        if not is_valid:
            logger.info(
                "Draft session #%d failed validation: %s", i + 1, validation_errors
            )
            errors.extend(validation_errors)

        # Check for overlaps if session is valid
        if is_valid:
            has_overlap, conflict_details = check_session_overlap(
                session, all_sessions[:i] + (existing_sessions or [])
            )
            if has_overlap:
                logger.warning(
                    "Draft session #%d has overlap: %s", i + 1, conflict_details
                )
                errors.extend(conflict_details)

        if errors:
            session_errors[i] = errors

    logger.info(
        "Draft session validation complete. All valid: %s", len(session_errors) == 0
    )
    return len(session_errors) == 0, session_errors


def is_weekend(check_date: date) -> bool:
    """
    Check if a date is a weekend.

    Args:
        check_date: Date to check

    Returns:
        True if weekend, False otherwise
    """
    logger.debug("Checking if date is weekend: %s", check_date)
    result = check_date.weekday() in WEEKEND_DAYS
    logger.debug("Weekend check result for %s: %s", check_date, result)
    return result


def get_weekend_info(check_date: date) -> Dict[str, Any]:
    """
    Get weekend information for a date.

    Args:
        check_date: Date to check

    Returns:
        Dictionary with weekend information
    """
    logger.debug("Getting weekend info for date: %s", check_date)
    is_weekend_day = is_weekend(check_date)

    info = {
        "is_weekend": is_weekend_day,
        "day_name": check_date.strftime("%A"),
        "message": (
            f"{check_date.strftime('%A')} is a weekend day"
            if is_weekend_day
            else f"{check_date.strftime('%A')} is a weekday"
        ),
        "requires_override": is_weekend_day,
    }
    logger.debug("Weekend info: %s", info)
    return info


def validate_date_for_scheduling(
    schedule_date: date,
) -> Tuple[bool, List[str], List[str]]:
    """
    Validate a date for scheduling purposes.

    Args:
        schedule_date: Date to validate

    Returns:
        Tuple of (is_valid, errors, warnings)
    """
    logger.info("Validating date for scheduling: %s", schedule_date)
    errors = []
    warnings = []

    today = date.today()
    if schedule_date < today:
        logger.warning("Scheduling for past date: %s", schedule_date)
        warnings.append(
            f"Scheduling for past date ({schedule_date.strftime('%Y-%m-%d')})"
        )

    if is_weekend(schedule_date):
        logger.warning("Selected date is a weekend: %s", schedule_date)
        warnings.append(
            f"Selected date is a weekend ({schedule_date.strftime('%A')}). Weekend override may be required."
        )

    days_in_future = (schedule_date - today).days
    if days_in_future > 365:
        logger.warning("Scheduling very far in future: %d days", days_in_future)
        warnings.append(f"Scheduling very far in future ({days_in_future} days)")

    logger.info("Date validation result: errors=%s, warnings=%s", errors, warnings)
    return len(errors) == 0, errors, warnings


def calculate_total_duration(sessions: List[Dict]) -> Dict[str, Any]:
    """
    Calculate total duration for a list of sessions.

    Args:
        sessions: List of session dictionaries

    Returns:
        Dictionary with duration information
    """
    logger.info(
        "Calculating total duration for %d sessions", len(sessions) if sessions else 0
    )

    if not sessions:
        logger.info("No sessions provided for duration calculation.")
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

            if end_dt > start_dt:
                duration = int((end_dt - start_dt).total_seconds() / 60)
                total_minutes += duration
                valid_sessions += 1
        except ValueError:
            logger.error("Invalid time format in session: %s", session)
            continue

    total_hours = total_minutes / 60.0
    hours = total_minutes // 60
    minutes = total_minutes % 60
    formatted = f"{hours}:{minutes:02d}"

    average_minutes = total_minutes // valid_sessions if valid_sessions > 0 else 0

    result = {
        "total_minutes": total_minutes,
        "total_hours": round(total_hours, 2),
        "formatted": formatted,
        "average_session_minutes": average_minutes,
        "valid_sessions": valid_sessions,
    }
    logger.info("Total duration calculation result: %s", result)
    return result


def get_time_conflicts_summary(sessions: List[Dict]) -> Dict[str, Any]:
    """
    Analyze sessions for time conflicts.

    Args:
        sessions: List of sessions to analyze

    Returns:
        Dictionary with conflict analysis
    """
    logger.info(
        "Analyzing sessions for time conflicts. Session count: %d",
        len(sessions) if sessions else 0,
    )
    conflicts = []

    for i, session1 in enumerate(sessions):
        for j, session2 in enumerate(sessions[i + 1 :], i + 1):
            has_overlap, conflict_details = check_session_overlap(session1, [session2])
            if has_overlap:
                logger.warning(
                    "Time conflict detected between session %d and %d: %s",
                    i,
                    j,
                    conflict_details,
                )
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

    result = {
        "has_conflicts": len(conflicts) > 0,
        "conflict_count": len(conflicts),
        "conflicts": conflicts,
    }
    logger.info("Time conflicts summary: %s", result)
    return result


def validate_submission_readiness(
    doctor_id: str,
    date: str,
    draft_sessions: List[Dict],
    existing_sessions: List[Dict] = None,
) -> Dict[str, Any]:
    """
    Validate that sessions are ready for submission.

    Args:
        doctor_id: Doctor ID
        date: Date string
        draft_sessions: List of draft sessions
        existing_sessions: List of existing sessions

    Returns:
        Dictionary with readiness information
    """
    logger.info(
        "Validating submission readiness for doctor_id=%s, date=%s", doctor_id, date
    )
    errors = []
    warnings = []

    if not draft_sessions:
        logger.warning("No sessions to submit.")
        errors.append("No sessions to submit")

    if existing_sessions is None:
        existing_sessions = []

    # Check daily session limit
    within_limit, limit_error = check_daily_session_limit(
        doctor_id, date, existing_sessions, draft_sessions
    )
    if not within_limit:
        logger.warning("Daily session limit validation failed: %s", limit_error)
        errors.append(limit_error)

    # Validate draft sessions
    if draft_sessions:
        all_valid, session_errors = validate_draft_sessions(
            draft_sessions, existing_sessions
        )
        if not all_valid:
            for session_idx, session_errs in session_errors.items():
                logger.warning(
                    "Session %d validation errors: %s", session_idx + 1, session_errs
                )
                errors.extend(
                    [f"Session {session_idx + 1}: {err}" for err in session_errs]
                )

    # Validate date
    try:
        schedule_date = datetime.strptime(date, "%Y-%m-%d").date()
        date_valid, date_errors, date_warnings = validate_date_for_scheduling(
            schedule_date
        )
        errors.extend(date_errors)
        warnings.extend(date_warnings)
    except ValueError:
        logger.error("Invalid date format: %s", date)
        errors.append("Invalid date format")

    # Check for time conflicts
    all_sessions = (existing_sessions or []) + draft_sessions
    conflict_analysis = get_time_conflicts_summary(all_sessions)
    if conflict_analysis["has_conflicts"]:
        for conflict in conflict_analysis["conflicts"]:
            logger.warning("Time conflict: %s", conflict["details"])
            errors.append(f"Time conflict: {conflict['details']}")

    # Calculate duration info
    duration_info = calculate_total_duration(draft_sessions)

    result = {
        "ready_for_submission": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
        "session_count": len(draft_sessions),
        "duration_info": duration_info,
        "conflict_analysis": conflict_analysis,
    }
    logger.info("Submission readiness result: %s", result)
    return result
