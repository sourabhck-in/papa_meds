# src/infrastructure/sheets/sheets_ops.py
"""
Google Sheets Operations for Medical Schedule Management System.

Replaces CSV operations with Google Sheets API calls.
Maintains same interface as data_ops.py for easy migration.
"""

import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
import os
import time
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
import uuid

from src.utils.logging_config import get_logger
from src.utils.config import (
    GOOGLE_CREDENTIALS_PATH,
    GOOGLE_SCOPES,
    DOCTORS_SHEET_NAME,
    SUBMISSIONS_SHEET_NAME,
    DOCTORS_COLUMNS,
    SUBMISSIONS_COLUMNS,
    GOOGLE_SHEETS_TIMEOUT,
    GOOGLE_SHEETS_RETRY_ATTEMPTS,
    GOOGLE_SHEETS_RATE_LIMIT_DELAY,
)

# Initialize logger
logger = get_logger(__name__)


class GoogleSheetsError(Exception):
    """Custom exception for Google Sheets operations"""

    pass


class SheetsClient:
    """
    Google Sheets client with connection management and error handling.
    """

    def __init__(self):
        self.client: Optional[gspread.Client] = None
        self.doctors_sheet: Optional[gspread.Worksheet] = None
        self.submissions_sheet: Optional[gspread.Worksheet] = None
        self._connect()

    # def _connect(self) -> None:
    #     """
    #     Establish connection to Google Sheets.

    #     Raises:
    #         GoogleSheetsError: If connection fails
    #     """
    #     try:
    #         logger.info("Connecting to Google Sheets API...")

    #         # Load credentials
    #         creds = Credentials.from_service_account_file(
    #             GOOGLE_CREDENTIALS_PATH, scopes=GOOGLE_SCOPES
    #         )

    #         # Create client
    #         self.client = gspread.authorize(creds)

    #         # Connect to specific sheets
    #         self.doctors_sheet = self.client.open(DOCTORS_SHEET_NAME).sheet1
    #         self.submissions_sheet = self.client.open(SUBMISSIONS_SHEET_NAME).sheet1

    #         logger.info("Successfully connected to Google Sheets")

    #     except FileNotFoundError:
    #         error_msg = f"Google credentials file not found: {GOOGLE_CREDENTIALS_PATH}"
    #         logger.error(error_msg)
    #         raise GoogleSheetsError(error_msg)

    #     except gspread.exceptions.SpreadsheetNotFound as e:
    #         error_msg = f"Google Sheet not found: {str(e)}"
    #         logger.error(error_msg)
    #         raise GoogleSheetsError(error_msg)

    #     except Exception as e:
    #         error_msg = f"Failed to connect to Google Sheets: {str(e)}"
    #         logger.error(error_msg)
    #         raise GoogleSheetsError(error_msg)

    def _connect(self) -> None:
        """
        Establish connection to Google Sheets.

        Raises:
            GoogleSheetsError: If connection fails
        """
        try:
            logger.info("Connecting to Google Sheets API...")

            # Load credentials
            creds = Credentials.from_service_account_file(
                GOOGLE_CREDENTIALS_PATH, scopes=GOOGLE_SCOPES
            )

            # Create client
            self.client = gspread.authorize(creds)

            # Connect to specific sheets
            self.doctors_sheet = self.client.open(DOCTORS_SHEET_NAME).sheet1
            self.submissions_sheet = self.client.open(SUBMISSIONS_SHEET_NAME).sheet1

            logger.info("Successfully connected to Google Sheets")

        except FileNotFoundError:
            error_msg = f"Google credentials file not found: {GOOGLE_CREDENTIALS_PATH}"
            logger.error(error_msg)
            raise GoogleSheetsError(f"🔐 Credentials Error: {error_msg}")

        except gspread.exceptions.SpreadsheetNotFound as e:
            error_msg = f"Google Sheet not found: {str(e)}"
            logger.error(error_msg)
            raise GoogleSheetsError(f"📊 Sheet Not Found: {error_msg}")

        except Exception as e:
            error_msg = f"Failed to connect to Google Sheets: {str(e)}"
            logger.error(error_msg)
            raise GoogleSheetsError(f"🌐 Connection Failed: {error_msg}")

    def _retry_operation(self, operation, *args, **kwargs):
        """
        Retry Google Sheets operations with exponential backoff.

        Args:
            operation: Function to retry
            *args, **kwargs: Arguments for the operation

        Returns:
            Result of the operation

        Raises:
            GoogleSheetsError: If all retries fail
        """
        last_exception = None

        for attempt in range(GOOGLE_SHEETS_RETRY_ATTEMPTS):
            try:
                if attempt > 0:
                    delay = GOOGLE_SHEETS_RATE_LIMIT_DELAY * (2**attempt)
                    logger.debug(
                        f"Retrying operation after {delay}s delay (attempt {attempt + 1})"
                    )
                    time.sleep(delay)

                return operation(*args, **kwargs)

            except Exception as e:
                last_exception = e
                logger.warning(f"Operation failed (attempt {attempt + 1}): {str(e)}")

                # If it's the last attempt, don't wait
                if attempt == GOOGLE_SHEETS_RETRY_ATTEMPTS - 1:
                    break

        # All retries failed
        error_msg = f"Operation failed after {GOOGLE_SHEETS_RETRY_ATTEMPTS} attempts: {str(last_exception)}"
        logger.error(error_msg)
        raise GoogleSheetsError(error_msg)

    def read_sheet_data(self, sheet: gspread.Worksheet) -> List[List[str]]:
        """
        Read all data from a Google Sheet.

        Args:
            sheet: Worksheet to read from

        Returns:
            List of rows (each row is a list of values)
        """

        def _read_operation():
            return sheet.get_all_values()

        return self._retry_operation(_read_operation)

    def write_sheet_data(self, sheet: gspread.Worksheet, data: List[List[str]]) -> None:
        """
        Write data to a Google Sheet (overwrites existing data).

        Args:
            sheet: Worksheet to write to
            data: Data to write (list of rows)
        """

        def _write_operation():
            sheet.clear()
            if data:
                sheet.update(data)

        self._retry_operation(_write_operation)

    def append_sheet_data(
        self, sheet: gspread.Worksheet, rows: List[List[str]]
    ) -> None:
        """
        Append new rows to a Google Sheet.

        Args:
            sheet: Worksheet to append to
            rows: Rows to append
        """

        def _append_operation():
            for row in rows:
                sheet.append_row(row)
                time.sleep(GOOGLE_SHEETS_RATE_LIMIT_DELAY)  # Rate limiting

        self._retry_operation(_append_operation)


# Global sheets client instance
_sheets_client: Optional[SheetsClient] = None


def get_sheets_client() -> SheetsClient:
    """
    Get the global Google Sheets client instance.

    Returns:
        SheetsClient instance
    """
    global _sheets_client
    if _sheets_client is None:
        _sheets_client = SheetsClient()
    return _sheets_client


# =============================================================================
# DATA OPERATIONS (SAME INTERFACE AS ORIGINAL data_ops.py)
# =============================================================================


def ensure_sheets_initialized() -> None:
    """
    Ensure Google Sheets are initialized with proper headers.
    Replaces ensure_csv_exists() from original code.
    """
    logger.info("Ensuring Google Sheets are initialized...")

    try:
        client = get_sheets_client()

        # Check doctors sheet
        doctors_data = client.read_sheet_data(client.doctors_sheet)
        if not doctors_data or doctors_data[0] != DOCTORS_COLUMNS:
            logger.info("Initializing doctors sheet with headers...")
            client.write_sheet_data(client.doctors_sheet, [DOCTORS_COLUMNS])

        # Check submissions sheet
        submissions_data = client.read_sheet_data(client.submissions_sheet)
        if not submissions_data or submissions_data[0] != SUBMISSIONS_COLUMNS:
            logger.info("Initializing submissions sheet with headers...")
            client.write_sheet_data(client.submissions_sheet, [SUBMISSIONS_COLUMNS])

        logger.info("Google Sheets initialization complete")

    except Exception as e:
        logger.error(f"Failed to initialize Google Sheets: {str(e)}")
        raise GoogleSheetsError(f"Failed to initialize sheets: {str(e)}")


def load_submissions(
    doctor_id: Optional[str] = None, date: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Load submissions from Google Sheets, optionally filtered by doctor and/or date.

    Args:
        doctor_id: Filter by doctor ID (optional)
        date: Filter by date in YYYY-MM-DD format (optional)

    Returns:
        List of submission dictionaries
    """
    logger.info(f"Loading submissions (doctor_id={doctor_id}, date={date})")

    try:
        client = get_sheets_client()

        # Read all data from submissions sheet
        sheet_data = client.read_sheet_data(client.submissions_sheet)

        if not sheet_data or len(sheet_data) < 2:  # No data beyond headers
            logger.info("No submission data found")
            return []

        # Convert to list of dictionaries
        headers = sheet_data[0]
        submissions = []

        for row in sheet_data[1:]:  # Skip header row
            # Pad row with empty strings if necessary
            padded_row = row + [""] * (len(headers) - len(row))
            submission = dict(zip(headers, padded_row))
            submissions.append(submission)

        # Apply filters if provided
        filtered_submissions = submissions

        if doctor_id:
            filtered_submissions = [
                s for s in filtered_submissions if s.get("doctor_id") == doctor_id
            ]

        if date:
            filtered_submissions = [
                s for s in filtered_submissions if s.get("date") == date
            ]

        logger.info(
            f"Loaded {len(filtered_submissions)} submissions (total: {len(submissions)})"
        )
        return filtered_submissions

    except Exception as e:
        logger.error(f"Error loading submissions: {str(e)}")
        raise GoogleSheetsError(f"Failed to load submissions: {str(e)}")


def save_sessions_to_sheets(
    draft_sessions: List[Dict[str, Any]], doctor_info: Dict[str, str], submitted_by: str
) -> bool:
    """
    Save draft sessions to Google Sheets as individual submission records.

    Args:
        draft_sessions: List of session dictionaries from st.session_state
        doctor_info: Dictionary with doctor information
        submitted_by: Username of person submitting

    Returns:
        bool: True if successful, False otherwise
    """
    logger.info(f"Saving {len(draft_sessions)} sessions to Google Sheets")

    try:
        if not draft_sessions:
            logger.warning("No sessions to save")
            return False

        client = get_sheets_client()
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Prepare new submission rows
        new_rows = []

        for session in draft_sessions:
            submission_record = [
                generate_submission_id(),
                doctor_info["id"],
                format_doctor_name(doctor_info),
                session["date"],
                session["start_time"],
                session["end_time"],
                session["scribe_name"],
                str(session["patient_number"]),
                submitted_by,
                current_time,
            ]
            new_rows.append(submission_record)

        # Append to submissions sheet
        client.append_sheet_data(client.submissions_sheet, new_rows)

        logger.info(f"Successfully saved {len(new_rows)} sessions to Google Sheets")
        return True

    except Exception as e:
        logger.error(f"Error saving sessions to Google Sheets: {str(e)}")
        return False


def get_existing_sessions(doctor_id: str, date: str) -> List[Dict[str, Any]]:
    """
    Get existing sessions for a specific doctor and date.

    Args:
        doctor_id: Doctor ID
        date: Date in YYYY-MM-DD format

    Returns:
        List of session dictionaries
    """
    logger.info(f"Getting existing sessions for doctor_id={doctor_id}, date={date}")

    try:
        submissions = load_submissions(doctor_id=doctor_id, date=date)

        # Convert submissions to session format for easier handling
        sessions = []
        for sub in submissions:
            session = {
                "submission_id": sub["submission_id"],
                "start_time": sub["start_time"],
                "end_time": sub["end_time"],
                "scribe_name": sub["scribe_name"],
                "patient_number": sub["patient_number"],
                "submitted_time": sub["submitted_time"],
            }
            sessions.append(session)

        logger.info(f"Found {len(sessions)} existing sessions")
        return sessions

    except Exception as e:
        logger.error(f"Error getting existing sessions: {str(e)}")
        return []


def update_submission(submission_id: str, updated_data: Dict[str, Any]) -> bool:
    """
    Update an existing submission record in Google Sheets.

    Args:
        submission_id: ID of submission to update
        updated_data: Dictionary with updated session data

    Returns:
        bool: True if successful, False otherwise
    """
    logger.info(f"Updating submission {submission_id}")

    try:
        client = get_sheets_client()

        # Read all submissions data
        sheet_data = client.read_sheet_data(client.submissions_sheet)

        if not sheet_data or len(sheet_data) < 2:
            logger.warning("No submissions found to update")
            return False

        headers = sheet_data[0]

        # Find the submission to update
        submission_row_index = None
        for i, row in enumerate(sheet_data[1:], 1):  # Start from 1 (skip header)
            if (
                len(row) > 0 and row[0] == submission_id
            ):  # submission_id is first column
                submission_row_index = i + 1  # +1 for sheet indexing (1-based)
                break

        if submission_row_index is None:
            logger.warning(f"Submission {submission_id} not found")
            return False

        # Update the row data
        updated_row = sheet_data[
            submission_row_index - 1
        ].copy()  # -1 for list indexing

        # Update fields that are provided
        field_mapping = {
            "start_time": 4,  # Column index in SUBMISSIONS_COLUMNS
            "end_time": 5,
            "scribe_name": 6,
            "patient_number": 7,
        }

        for field, value in updated_data.items():
            if field in field_mapping:
                col_index = field_mapping[field]
                updated_row[col_index] = str(value)

        # Update submission time
        updated_row[9] = datetime.now().strftime(
            "%Y-%m-%d %H:%M:%S"
        )  # submitted_time column

        # Write back to sheet
        sheet_data[submission_row_index - 1] = updated_row
        client.write_sheet_data(client.submissions_sheet, sheet_data)

        logger.info(f"Successfully updated submission {submission_id}")
        return True

    except Exception as e:
        logger.error(f"Error updating submission: {str(e)}")
        return False


def delete_submission(submission_id: str) -> bool:
    """
    Delete a submission record from Google Sheets.

    Args:
        submission_id: ID of submission to delete

    Returns:
        bool: True if successful, False otherwise
    """
    logger.info(f"Deleting submission {submission_id}")

    try:
        client = get_sheets_client()

        # Read all submissions data
        sheet_data = client.read_sheet_data(client.submissions_sheet)

        if not sheet_data or len(sheet_data) < 2:
            logger.warning("No submissions found to delete")
            return False

        # Find and remove the submission
        headers = sheet_data[0]
        filtered_data = [headers]  # Keep headers

        found = False
        for row in sheet_data[1:]:  # Skip header
            if len(row) > 0 and row[0] == submission_id:
                found = True
                logger.info(f"Found submission {submission_id} for deletion")
                # Skip this row (don't add to filtered_data)
            else:
                filtered_data.append(row)

        if not found:
            logger.warning(f"Submission {submission_id} not found for deletion")
            return False

        # Write back to sheet
        client.write_sheet_data(client.submissions_sheet, filtered_data)

        logger.info(f"Successfully deleted submission {submission_id}")
        return True

    except Exception as e:
        logger.error(f"Error deleting submission: {str(e)}")
        return False


def get_day_summary(doctor_id: str, date: str) -> Dict[str, Any]:
    """
    Get summary information for a doctor's day.

    Args:
        doctor_id: Doctor ID
        date: Date in YYYY-MM-DD format

    Returns:
        Dictionary with day summary
    """
    logger.info(f"Getting day summary for doctor_id={doctor_id}, date={date}")

    try:
        sessions = get_existing_sessions(doctor_id, date)

        if not sessions:
            return {
                "doctor_id": doctor_id,
                "date": date,
                "total_sessions": 0,
                "total_hours": 0.0,
                "sessions": [],
            }

        # Calculate total duration
        total_minutes = 0
        for session in sessions:
            try:
                start_time = datetime.strptime(session["start_time"], "%H:%M")
                end_time = datetime.strptime(session["end_time"], "%H:%M")
                duration = (end_time - start_time).total_seconds() / 60
                total_minutes += duration
            except ValueError:
                logger.warning(f"Invalid time format in session: {session}")
                continue

        total_hours = total_minutes / 60.0

        summary = {
            "doctor_id": doctor_id,
            "date": date,
            "total_sessions": len(sessions),
            "total_hours": round(total_hours, 2),
            "sessions": sessions,
        }

        logger.info(f"Day summary: {len(sessions)} sessions, {total_hours:.2f} hours")
        return summary

    except Exception as e:
        logger.error(f"Error getting day summary: {str(e)}")
        return {
            "doctor_id": doctor_id,
            "date": date,
            "total_sessions": 0,
            "total_hours": 0.0,
            "sessions": [],
        }


def load_doctors() -> List[Dict[str, str]]:
    """
    Load doctors data from Google Sheets.

    Returns:
        List of doctor dictionaries
    """
    logger.info("Loading doctors data from Google Sheets")

    try:
        client = get_sheets_client()

        # Read doctors sheet data
        sheet_data = client.read_sheet_data(client.doctors_sheet)

        if not sheet_data or len(sheet_data) < 2:  # No data beyond headers
            logger.warning("No doctors data found")
            return []

        # Convert to list of dictionaries
        headers = sheet_data[0]
        doctors = []

        for row in sheet_data[1:]:  # Skip header row
            # Pad row with empty strings if necessary
            padded_row = row + [""] * (len(headers) - len(row))
            doctor = dict(zip(headers, padded_row))
            doctors.append(doctor)

        logger.info(f"Loaded {len(doctors)} doctors")
        return doctors

    except Exception as e:
        logger.error(f"Error loading doctors: {str(e)}")
        return []


def save_doctors_to_sheets(doctors: List[Dict[str, str]]) -> bool:
    """
    Save doctors data to Google Sheets.

    Args:
        doctors: List of doctor dictionaries

    Returns:
        bool: True if successful, False otherwise
    """
    logger.info(f"Saving {len(doctors)} doctors to Google Sheets")

    try:
        if not doctors:
            logger.warning("No doctors to save")
            return False

        client = get_sheets_client()

        # Prepare data for sheets
        sheet_data = [DOCTORS_COLUMNS]  # Headers first

        for doctor in doctors:
            row = [
                doctor.get("doctor_id", ""),
                doctor.get("clinic", ""),
                doctor.get("fn", ""),
                doctor.get("ln", ""),
                doctor.get("tl_name", ""),
                doctor.get("full_name", ""),
            ]
            sheet_data.append(row)

        # Write to sheet
        client.write_sheet_data(client.doctors_sheet, sheet_data)

        logger.info(f"Successfully saved {len(doctors)} doctors to Google Sheets")
        return True

    except Exception as e:
        logger.error(f"Error saving doctors to Google Sheets: {str(e)}")
        return False


# =============================================================================
# HELPER FUNCTIONS (SAME AS ORIGINAL)
# =============================================================================


def generate_submission_id() -> str:
    """Generate unique submission ID"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    unique_part = uuid.uuid4().hex[:6].upper()
    submission_id = f"SUB_{timestamp}_{unique_part}"
    logger.debug(f"Generated submission ID: {submission_id}")
    return submission_id


def format_doctor_name(doctor_info: Dict[str, str]) -> str:
    """Format doctor name in standard format"""
    name = f"{doctor_info['clinic']} | {doctor_info['fn']} | {doctor_info['ln']}"
    logger.debug(f"Formatted doctor name: {name}")
    return name


def format_doctor_first_last_name(doctor_info: Dict[str, str]) -> str:
    """Format doctor name as 'First Last'"""
    name = f"{doctor_info['fn']} {doctor_info['ln']}"
    logger.debug(f"Formatted first-last name: {name}")
    return name


def calculate_duration_minutes(start_time: str, end_time: str) -> int:
    """
    Calculate session duration in minutes.

    Args:
        start_time: Start time in HH:MM format
        end_time: End time in HH:MM format

    Returns:
        Duration in minutes
    """
    try:
        start = datetime.strptime(start_time, "%H:%M")
        end = datetime.strptime(end_time, "%H:%M")

        # Handle sessions that cross midnight (unlikely but possible)
        if end < start:
            end = end.replace(day=end.day + 1)

        duration = int((end - start).total_seconds() / 60)
        logger.debug(
            f"Calculated duration: {start_time} to {end_time} = {duration} minutes"
        )
        return duration

    except ValueError as e:
        logger.error(
            f"Error calculating duration for {start_time} to {end_time}: {str(e)}"
        )
        return 0


# =============================================================================
# DATA VALIDATION AND STATS
# =============================================================================


def validate_sheets_connection() -> bool:
    """
    Validate that Google Sheets connection is working.

    Returns:
        True if connection is valid, False otherwise
    """
    logger.info("Validating Google Sheets connection...")

    try:
        client = get_sheets_client()

        # Test reading from both sheets
        doctors_data = client.read_sheet_data(client.doctors_sheet)
        submissions_data = client.read_sheet_data(client.submissions_sheet)

        logger.info("Google Sheets connection validation successful")
        return True

    except Exception as e:
        logger.error(f"Google Sheets connection validation failed: {str(e)}")
        return False


def get_sheets_stats() -> Dict[str, Any]:
    """
    Get statistics about the Google Sheets data.

    Returns:
        Dictionary with statistics
    """
    logger.info("Getting Google Sheets statistics")

    try:
        # Load all data
        doctors = load_doctors()
        submissions = load_submissions()

        if not submissions:
            return {
                "total_submissions": 0,
                "unique_doctors": 0,
                "date_range": None,
                "total_doctors": len(doctors),
                "connection_status": "Connected",
            }

        # Calculate stats
        unique_doctors = len(set(sub["doctor_id"] for sub in submissions))
        dates = [sub["date"] for sub in submissions if sub["date"]]

        stats = {
            "total_submissions": len(submissions),
            "unique_doctors": unique_doctors,
            "total_doctors": len(doctors),
            "date_range": {
                "earliest": min(dates) if dates else None,
                "latest": max(dates) if dates else None,
            },
            "connection_status": "Connected",
        }

        logger.info(f"Sheets stats: {stats}")
        return stats

    except Exception as e:
        logger.error(f"Error getting sheets stats: {str(e)}")
        return {
            "total_submissions": 0,
            "unique_doctors": 0,
            "date_range": None,
            "total_doctors": 0,
            "connection_status": f"Error: {str(e)}",
        }


# =============================================================================
# BULK OPERATIONS
# =============================================================================


def bulk_import_submissions(submissions: List[Dict[str, Any]]) -> Tuple[bool, str]:
    """
    Bulk import submissions to Google Sheets.

    Args:
        submissions: List of submission dictionaries

    Returns:
        Tuple of (success, message)
    """
    logger.info(f"Bulk importing {len(submissions)} submissions")

    try:
        if not submissions:
            return False, "No submissions to import"

        client = get_sheets_client()

        # Prepare rows for import
        rows = []
        for submission in submissions:
            row = [
                submission.get("submission_id", generate_submission_id()),
                submission.get("doctor_id", ""),
                submission.get("doctor_name", ""),
                submission.get("date", ""),
                submission.get("start_time", ""),
                submission.get("end_time", ""),
                submission.get("scribe_name", ""),
                str(submission.get("patient_number", "")),
                submission.get("submitted_by", ""),
                submission.get(
                    "submitted_time", datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                ),
            ]
            rows.append(row)

        # Append all rows
        client.append_sheet_data(client.submissions_sheet, rows)

        success_msg = f"Successfully imported {len(submissions)} submissions"
        logger.info(success_msg)
        return True, success_msg

    except Exception as e:
        error_msg = f"Error during bulk import: {str(e)}"
        logger.error(error_msg)
        return False, error_msg


def backup_sheets_data() -> Tuple[bool, str]:
    """
    Backup all Google Sheets data.

    Returns:
        Tuple of (success, message)
    """
    logger.info("Creating backup of Google Sheets data")

    try:
        client = get_sheets_client()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Read all data
        doctors_data = client.read_sheet_data(client.doctors_sheet)
        submissions_data = client.read_sheet_data(client.submissions_sheet)

        # Save to local files (for backup)
        backup_dir = f"backups/sheets_backup_{timestamp}"
        os.makedirs(backup_dir, exist_ok=True)

        # Save as CSV files
        if doctors_data:
            doctors_df = pd.DataFrame(doctors_data[1:], columns=doctors_data[0])
            doctors_df.to_csv(f"{backup_dir}/doctors_backup.csv", index=False)

        if submissions_data:
            submissions_df = pd.DataFrame(
                submissions_data[1:], columns=submissions_data[0]
            )
            submissions_df.to_csv(f"{backup_dir}/submissions_backup.csv", index=False)

        success_msg = f"Backup created successfully in {backup_dir}"
        logger.info(success_msg)
        return True, success_msg

    except Exception as e:
        error_msg = f"Error creating backup: {str(e)}"
        logger.error(error_msg)
        return False, error_msg
