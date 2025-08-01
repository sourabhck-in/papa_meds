# src/infrastructure/auth/google_auth.py
"""
Google Authentication module for Medical Schedule Management System.

Handles service account authentication and credential management
for Google Sheets API access.
"""

import os
import json
from typing import Optional, Dict, Any, Tuple, List
from google.oauth2.service_account import Credentials
import gspread

from src.utils.logging_config import get_logger
from src.utils.config import (
    GOOGLE_CREDENTIALS_PATH,
    GOOGLE_SCOPES,
    GOOGLE_SHEETS_TIMEOUT,
)

# Initialize logger
logger = get_logger(__name__)


class AuthenticationError(Exception):
    """Custom exception for authentication failures"""

    pass


class GoogleAuthenticator:
    """
    Handles Google service account authentication and credential validation.
    """

    def __init__(self, credentials_path: Optional[str] = None):
        """
        Initialize Google authenticator.

        Args:
            credentials_path: Path to service account JSON file
        """
        self.credentials_path = credentials_path or GOOGLE_CREDENTIALS_PATH
        self.credentials: Optional[Credentials] = None
        self.service_account_info: Optional[Dict[str, Any]] = None

        logger.info(
            f"Initializing Google authenticator with credentials: {self.credentials_path}"
        )

    def validate_credentials_file(self) -> bool:
        """
        Validate that credentials file exists and is properly formatted.

        Returns:
            True if valid, False otherwise

        Raises:
            AuthenticationError: If credentials are invalid
        """
        logger.info("Validating Google credentials file...")

        # Check if file exists
        if not os.path.exists(self.credentials_path):
            error_msg = f"Credentials file not found: {self.credentials_path}"
            logger.error(error_msg)
            raise AuthenticationError(error_msg)

        # Check if file is readable and valid JSON
        try:
            with open(self.credentials_path, "r") as f:
                creds_data = json.load(f)

            # Validate required fields for service account
            required_fields = [
                "type",
                "project_id",
                "private_key_id",
                "private_key",
                "client_email",
                "client_id",
                "auth_uri",
                "token_uri",
            ]

            missing_fields = [
                field for field in required_fields if field not in creds_data
            ]
            if missing_fields:
                error_msg = f"Missing required fields in credentials: {missing_fields}"
                logger.error(error_msg)
                raise AuthenticationError(error_msg)

            # Validate service account type
            if creds_data.get("type") != "service_account":
                error_msg = f"Invalid credential type: {creds_data.get('type')}. Expected 'service_account'"
                logger.error(error_msg)
                raise AuthenticationError(error_msg)

            # Store service account info for reference
            self.service_account_info = {
                "project_id": creds_data.get("project_id"),
                "client_email": creds_data.get("client_email"),
                "private_key_id": creds_data.get("private_key_id"),
            }

            logger.info(
                f"Credentials validation successful for project: {self.service_account_info['project_id']}"
            )
            logger.info(
                f"Service account email: {self.service_account_info['client_email']}"
            )

            return True

        except json.JSONDecodeError as e:
            error_msg = f"Invalid JSON in credentials file: {str(e)}"
            logger.error(error_msg)
            raise AuthenticationError(error_msg)

        except Exception as e:
            error_msg = f"Error validating credentials file: {str(e)}"
            logger.error(error_msg)
            raise AuthenticationError(error_msg)

    def authenticate(self) -> Credentials:
        """
        Authenticate with Google using service account credentials.

        Returns:
            Authenticated Credentials object

        Raises:
            AuthenticationError: If authentication fails
        """
        logger.info("Authenticating with Google service account...")

        try:
            # Validate credentials file first
            self.validate_credentials_file()

            # Create credentials from service account file
            self.credentials = Credentials.from_service_account_file(
                self.credentials_path, scopes=GOOGLE_SCOPES
            )

            logger.info("Google authentication successful")
            return self.credentials

        except Exception as e:
            error_msg = f"Authentication failed: {str(e)}"
            logger.error(error_msg)
            raise AuthenticationError(error_msg)

    def create_gspread_client(self) -> gspread.Client:
        """
        Create an authenticated gspread client.

        Returns:
            Authenticated gspread client

        Raises:
            AuthenticationError: If client creation fails
        """
        logger.info("Creating gspread client...")

        try:
            # Authenticate if not already done
            if self.credentials is None:
                self.authenticate()

            # Create gspread client
            client = gspread.authorize(self.credentials)

            logger.info("gspread client created successfully")
            return client

        except Exception as e:
            error_msg = f"Failed to create gspread client: {str(e)}"
            logger.error(error_msg)
            raise AuthenticationError(error_msg)

    def test_connection(self) -> Tuple[bool, str]:
        """
        Test the Google Sheets connection.

        Returns:
            Tuple of (success, message)
        """
        logger.info("Testing Google Sheets connection...")

        try:
            client = self.create_gspread_client()

            # Try to list available spreadsheets (basic connectivity test)
            # This is a lightweight operation that confirms authentication works
            client.list_permissions(
                "test"
            )  # This will fail gracefully if no permissions

            success_msg = f"Connection test successful for {self.service_account_info['client_email']}"
            logger.info(success_msg)
            return True, success_msg

        except Exception as e:
            # Connection test failure is expected if we don't have a test sheet
            # The important thing is that authentication worked
            if "not found" in str(e).lower():
                success_msg = (
                    "Authentication successful (test sheet not found, but auth works)"
                )
                logger.info(success_msg)
                return True, success_msg

            error_msg = f"Connection test failed: {str(e)}"
            logger.error(error_msg)
            return False, error_msg

    def get_account_info(self) -> Dict[str, str]:
        """
        Get service account information.

        Returns:
            Dictionary with account information
        """
        if self.service_account_info is None:
            self.validate_credentials_file()

        return self.service_account_info.copy()


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================


def create_authenticated_client() -> gspread.Client:
    """
    Create an authenticated Google Sheets client with default settings.

    Returns:
        Authenticated gspread client

    Raises:
        AuthenticationError: If authentication fails
    """
    logger.info("Creating authenticated Google Sheets client...")

    authenticator = GoogleAuthenticator()
    return authenticator.create_gspread_client()


def test_google_authentication() -> Tuple[bool, str]:
    """
    Test Google authentication and return status.

    Returns:
        Tuple of (success, status_message)
    """
    logger.info("Testing Google authentication...")

    try:
        authenticator = GoogleAuthenticator()
        return authenticator.test_connection()

    except AuthenticationError as e:
        return False, str(e)

    except Exception as e:
        error_msg = f"Unexpected error during authentication test: {str(e)}"
        logger.error(error_msg)
        return False, error_msg


def get_service_account_info() -> Optional[Dict[str, str]]:
    """
    Get service account information without authenticating.

    Returns:
        Service account info dictionary or None if unavailable
    """
    try:
        authenticator = GoogleAuthenticator()
        return authenticator.get_account_info()

    except Exception as e:
        logger.error(f"Error getting service account info: {str(e)}")
        return None


def validate_google_setup() -> Tuple[bool, List[str]]:
    """
    Validate complete Google Sheets setup.

    Returns:
        Tuple of (is_valid, list_of_issues)
    """
    logger.info("Validating complete Google Sheets setup...")

    issues = []

    try:
        # Test authentication
        auth_success, auth_message = test_google_authentication()
        if not auth_success:
            issues.append(f"Authentication failed: {auth_message}")

        # Check credentials file permissions
        if not os.access(GOOGLE_CREDENTIALS_PATH, os.R_OK):
            issues.append(f"Cannot read credentials file: {GOOGLE_CREDENTIALS_PATH}")

        # Validate scopes
        if not GOOGLE_SCOPES:
            issues.append("No Google API scopes configured")

        # Check required scopes
        required_scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive",
        ]

        missing_scopes = [
            scope for scope in required_scopes if scope not in GOOGLE_SCOPES
        ]
        if missing_scopes:
            issues.append(f"Missing required scopes: {missing_scopes}")

        is_valid = len(issues) == 0

        if is_valid:
            logger.info("Google Sheets setup validation successful")
        else:
            logger.warning(f"Google Sheets setup validation failed: {issues}")

        return is_valid, issues

    except Exception as e:
        error_msg = f"Error during setup validation: {str(e)}"
        logger.error(error_msg)
        return False, [error_msg]
