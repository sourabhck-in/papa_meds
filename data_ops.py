# data_ops.py - Simple CSV Operations for Medical Schedule Management
# No classes, just simple functions for reading/writing submissions.csv

import pandas as pd
import os
from datetime import datetime
from typing import List, Dict, Any, Optional
import uuid

from config import SUBMISSIONS_FILE, SUBMISSIONS_CSV_COLUMNS


def ensure_csv_exists():
    """Create submissions.csv with headers if it doesn't exist"""
    if not os.path.exists(SUBMISSIONS_FILE):
        # Create empty CSV with headers
        df = pd.DataFrame(columns=SUBMISSIONS_CSV_COLUMNS)
        df.to_csv(SUBMISSIONS_FILE, index=False)
        print(f"Created {SUBMISSIONS_FILE} with headers")


def load_submissions(
    doctor_id: Optional[str] = None, date: Optional[str] = None
) -> List[Dict]:
    """
    Load submissions from CSV, optionally filtered by doctor and/or date.

    Args:
        doctor_id: Filter by doctor ID (optional)
        date: Filter by date in YYYY-MM-DD format (optional)

    Returns:
        List of submission dictionaries
    """
    try:
        ensure_csv_exists()

        # Read CSV
        df = pd.read_csv(SUBMISSIONS_FILE)

        # Return empty list if no data
        if df.empty:
            return []

        # Apply filters if provided
        if doctor_id:
            df = df[df["doctor_id"] == doctor_id]

        if date:
            df = df[df["date"] == date]

        # Convert to list of dictionaries
        submissions = df.to_dict("records")

        print(
            f"Loaded {len(submissions)} submissions (doctor_id={doctor_id}, date={date})"
        )
        return submissions

    except Exception as e:
        print(f"Error loading submissions: {str(e)}")
        return []


def save_sessions_to_csv(
    draft_sessions: List[Dict], doctor_info: Dict, submitted_by: str
) -> bool:
    """
    Save draft sessions to CSV as individual submission records.

    Args:
        draft_sessions: List of session dictionaries from st.session_state
        doctor_info: Dictionary with doctor information
        submitted_by: Username of person submitting

    Returns:
        bool: True if successful, False otherwise
    """
    try:
        if not draft_sessions:
            print("No sessions to save")
            return False

        ensure_csv_exists()

        # Load existing submissions
        existing_df = pd.read_csv(SUBMISSIONS_FILE)

        # Prepare new submission records
        new_submissions = []
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        for session in draft_sessions:
            submission_record = {
                "submission_id": generate_submission_id(),
                "doctor_id": doctor_info["id"],
                "doctor_name": format_doctor_name(doctor_info),
                "date": session["date"],
                "start_time": session["start_time"],
                "end_time": session["end_time"],
                "scribe_name": session["scribe_name"],
                "patient_number": session["patient_number"],
                "submitted_by": submitted_by,
                "submitted_time": current_time,
            }
            new_submissions.append(submission_record)

        # Create DataFrame for new submissions
        new_df = pd.DataFrame(new_submissions)

        # Combine with existing data
        if not existing_df.empty:
            combined_df = pd.concat([existing_df, new_df], ignore_index=True)
        else:
            combined_df = new_df

        # Save to CSV
        combined_df.to_csv(SUBMISSIONS_FILE, index=False)

        print(f"Successfully saved {len(new_submissions)} sessions to CSV")
        return True

    except Exception as e:
        print(f"Error saving sessions to CSV: {str(e)}")
        return False


def get_existing_sessions(doctor_id: str, date: str) -> List[Dict]:
    """
    Get existing sessions for a specific doctor and date.

    Args:
        doctor_id: Doctor ID
        date: Date in YYYY-MM-DD format

    Returns:
        List of session dictionaries
    """
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

        return sessions

    except Exception as e:
        print(f"Error getting existing sessions: {str(e)}")
        return []


def update_submission(submission_id: str, updated_data: Dict) -> bool:
    """
    Update an existing submission record.

    Args:
        submission_id: ID of submission to update
        updated_data: Dictionary with updated session data

    Returns:
        bool: True if successful, False otherwise
    """
    try:
        ensure_csv_exists()

        # Load existing data
        df = pd.read_csv(SUBMISSIONS_FILE)

        if df.empty:
            print(f"No submissions found to update")
            return False

        # Find the submission to update
        submission_index = df[df["submission_id"] == submission_id].index

        if len(submission_index) == 0:
            print(f"Submission {submission_id} not found")
            return False

        # Update the record
        index = submission_index[0]

        # Update fields that are provided
        if "start_time" in updated_data:
            df.at[index, "start_time"] = updated_data["start_time"]
        if "end_time" in updated_data:
            df.at[index, "end_time"] = updated_data["end_time"]
        if "scribe_name" in updated_data:
            df.at[index, "scribe_name"] = updated_data["scribe_name"]
        if "patient_number" in updated_data:
            df.at[index, "patient_number"] = updated_data["patient_number"]

        # Always update the submission time to track when it was last modified
        df.at[index, "submitted_time"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Save back to CSV
        df.to_csv(SUBMISSIONS_FILE, index=False)

        print(f"Successfully updated submission {submission_id}")
        return True

    except Exception as e:
        print(f"Error updating submission: {str(e)}")
        return False


def delete_submission(submission_id: str) -> bool:
    """
    Delete a submission record.

    Args:
        submission_id: ID of submission to delete

    Returns:
        bool: True if successful, False otherwise
    """
    try:
        ensure_csv_exists()

        # Load existing data
        df = pd.read_csv(SUBMISSIONS_FILE)

        if df.empty:
            print(f"No submissions found to delete")
            return False

        # Check if submission exists
        if submission_id not in df["submission_id"].values:
            print(f"Submission {submission_id} not found")
            return False

        # Remove the submission
        df = df[df["submission_id"] != submission_id]

        # Save back to CSV
        df.to_csv(SUBMISSIONS_FILE, index=False)

        print(f"Successfully deleted submission {submission_id}")
        return True

    except Exception as e:
        print(f"Error deleting submission: {str(e)}")
        return False


def get_day_summary(doctor_id: str, date: str) -> Dict:
    """
    Get summary information for a doctor's day.

    Args:
        doctor_id: Doctor ID
        date: Date in YYYY-MM-DD format

    Returns:
        Dictionary with day summary
    """
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
            start_time = datetime.strptime(session["start_time"], "%H:%M")
            end_time = datetime.strptime(session["end_time"], "%H:%M")
            duration = (end_time - start_time).total_seconds() / 60
            total_minutes += duration

        total_hours = total_minutes / 60.0

        return {
            "doctor_id": doctor_id,
            "date": date,
            "total_sessions": len(sessions),
            "total_hours": round(total_hours, 2),
            "sessions": sessions,
        }

    except Exception as e:
        print(f"Error getting day summary: {str(e)}")
        return {
            "doctor_id": doctor_id,
            "date": date,
            "total_sessions": 0,
            "total_hours": 0.0,
            "sessions": [],
        }


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================


def generate_submission_id() -> str:
    """Generate unique submission ID"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    unique_part = uuid.uuid4().hex[:6].upper()
    return f"SUB_{timestamp}_{unique_part}"


def format_doctor_name(doctor_info: Dict) -> str:
    """Format doctor name in standard format"""
    return f"{doctor_info['clinic']} | {doctor_info['fn']} | {doctor_info['ln']}"


def format_doctor_first_last_name(doctor_info: Dict) -> str:
    """Format doctor name as 'First Last'"""
    return f"{doctor_info['fn']} {doctor_info['ln']}"


def calculate_duration_minutes(start_time: str, end_time: str) -> int:
    """Calculate session duration in minutes"""
    try:
        start = datetime.strptime(start_time, "%H:%M")
        end = datetime.strptime(end_time, "%H:%M")

        # Handle sessions that cross midnight (unlikely but possible)
        if end < start:
            end = end.replace(day=end.day + 1)

        duration = (end - start).total_seconds() / 60
        return int(duration)

    except ValueError:
        return 0


# =============================================================================
# DATA VALIDATION HELPERS
# =============================================================================


def validate_csv_structure() -> bool:
    """Validate that CSV has correct structure"""
    try:
        if not os.path.exists(SUBMISSIONS_FILE):
            return False

        df = pd.read_csv(SUBMISSIONS_FILE)

        # Check if all required columns exist
        missing_columns = set(SUBMISSIONS_CSV_COLUMNS) - set(df.columns)
        if missing_columns:
            print(f"Missing columns in CSV: {missing_columns}")
            return False

        return True

    except Exception as e:
        print(f"Error validating CSV structure: {str(e)}")
        return False


def get_csv_stats() -> Dict:
    """Get statistics about the CSV file"""
    try:
        ensure_csv_exists()
        df = pd.read_csv(SUBMISSIONS_FILE)

        if df.empty:
            return {
                "total_submissions": 0,
                "unique_doctors": 0,
                "date_range": None,
                "file_size_kb": 0,
            }

        file_size = os.path.getsize(SUBMISSIONS_FILE) / 1024  # KB

        return {
            "total_submissions": len(df),
            "unique_doctors": df["doctor_id"].nunique(),
            "date_range": {"earliest": df["date"].min(), "latest": df["date"].max()},
            "file_size_kb": round(file_size, 2),
        }

    except Exception as e:
        print(f"Error getting CSV stats: {str(e)}")
        return {
            "total_submissions": 0,
            "unique_doctors": 0,
            "date_range": None,
            "file_size_kb": 0,
        }
