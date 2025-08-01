# src/infrastructure/auth/google_auth.py
"""
Google Authentication module for Medical Schedule Management System.
Updated to work with both local development and Streamlit Cloud secrets.
"""

import os
import json
import streamlit as st
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


def get_google_credentials() -> Credentials:
    """
    Get Google credentials from Streamlit secrets or local file.

    Returns:
        Authenticated Credentials object

    Raises:
        AuthenticationError: If credentials cannot be loaded
    """
    logger.info("Loading Google credentials...")

    # Method 1: Try Streamlit secrets (for cloud deployment)
    try:
        if hasattr(st, "secrets") and "gcp_service_account" in st.secrets:
            logger.info("Attempting to load credentials from Streamlit secrets...")

            # Convert secrets to service account info dictionary
            service_account_info = dict(st.secrets["gcp_service_account"])

            # Validate required fields
            required_fields = ["type", "project_id", "private_key", "client_email"]
            missing_fields = [
                field for field in required_fields if field not in service_account_info
            ]

            if missing_fields:
                raise AuthenticationError(
                    f"Missing required fields in secrets: {missing_fields}"
                )

            # Create credentials from service account info
            credentials = Credentials.from_service_account_info(
                service_account_info, scopes=GOOGLE_SCOPES
            )

            logger.info("Successfully loaded credentials from Streamlit secrets")
            logger.info(f"Service account: {service_account_info.get('client_email')}")
            return credentials

    except Exception as e:
        logger.warning(f"Could not load from Streamlit secrets: {str(e)}")

    # Method 2: Try local file (for local development)
    try:
        if os.path.exists(GOOGLE_CREDENTIALS_PATH):
            logger.info(
                f"Attempting to load credentials from local file: {GOOGLE_CREDENTIALS_PATH}"
            )

            credentials = Credentials.from_service_account_file(
                GOOGLE_CREDENTIALS_PATH, scopes=GOOGLE_SCOPES
            )

            logger.info("Successfully loaded credentials from local file")
            return credentials
        else:
            logger.warning(
                f"Local credentials file not found: {GOOGLE_CREDENTIALS_PATH}"
            )

    except Exception as e:
        logger.warning(f"Could not load from local file: {str(e)}")

    # Method 3: Try environment variable (alternative method)
    try:
        google_creds_env = os.getenv("GOOGLE_APPLICATION_CREDENTIALS_JSON")
        if google_creds_env:
            logger.info("Attempting to load credentials from environment variable...")

            service_account_info = json.loads(google_creds_env)
            credentials = Credentials.from_service_account_info(
                service_account_info, scopes=GOOGLE_SCOPES
            )

            logger.info("Successfully loaded credentials from environment variable")
            return credentials

    except Exception as e:
        logger.warning(f"Could not load from environment variable: {str(e)}")

    # If all methods fail
    error_msg = (
        "Could not load Google credentials from any source. "
        "Please check:\n"
        "1. Streamlit secrets are configured correctly\n"
        "2. Local credentials file exists at the correct path\n"
        "3. Environment variables are set properly"
    )
    logger.error(error_msg)
    raise AuthenticationError(error_msg)


class GoogleAuthenticator:
    """
    Handles Google service account authentication and credential validation.
    Updated to work with Streamlit Cloud secrets.
    """

    def __init__(self, credentials_path: Optional[str] = None):
        """
        Initialize Google authenticator.

        Args:
            credentials_path: Path to service account JSON file (for local dev)
        """
        self.credentials_path = credentials_path or GOOGLE_CREDENTIALS_PATH
        self.credentials: Optional[Credentials] = None
        self.service_account_info: Optional[Dict[str, Any]] = None

        logger.info("Initializing Google authenticator...")

    def validate_credentials_file(self) -> bool:
        """
        Validate that credentials file exists and is properly formatted.
        Note: This is mainly for local development.

        Returns:
            True if valid, False otherwise
        """
        logger.info("Validating Google credentials...")

        # For Streamlit Cloud, check secrets first
        try:
            if hasattr(st, "secrets") and "gcp_service_account" in st.secrets:
                secrets_info = dict(st.secrets["gcp_service_account"])

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
                    field for field in required_fields if field not in secrets_info
                ]
                if missing_fields:
                    error_msg = f"Missing required fields in Streamlit secrets: {missing_fields}"
                    logger.error(error_msg)
                    raise AuthenticationError(error_msg)

                if secrets_info.get("type") != "service_account":
                    error_msg = f"Invalid credential type in secrets: {secrets_info.get('type')}"
                    logger.error(error_msg)
                    raise AuthenticationError(error_msg)

                self.service_account_info = {
                    "project_id": secrets_info.get("project_id"),
                    "client_email": secrets_info.get("client_email"),
                    "private_key_id": secrets_info.get("private_key_id"),
                }

                logger.info("Streamlit secrets validation successful")
                logger.info(f"Project: {self.service_account_info['project_id']}")
                logger.info(
                    f"Service account: {self.service_account_info['client_email']}"
                )
                return True

        except Exception as e:
            logger.warning(f"Streamlit secrets validation failed: {str(e)}")

        # Fallback to local file validation
        if not os.path.exists(self.credentials_path):
            error_msg = f"Credentials file not found: {self.credentials_path}"
            logger.error(error_msg)
            raise AuthenticationError(error_msg)

        try:
            with open(self.credentials_path, "r") as f:
                creds_data = json.load(f)

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
                error_msg = (
                    f"Missing required fields in credentials file: {missing_fields}"
                )
                logger.error(error_msg)
                raise AuthenticationError(error_msg)

            if creds_data.get("type") != "service_account":
                error_msg = f"Invalid credential type: {creds_data.get('type')}"
                logger.error(error_msg)
                raise AuthenticationError(error_msg)

            self.service_account_info = {
                "project_id": creds_data.get("project_id"),
                "client_email": creds_data.get("client_email"),
                "private_key_id": creds_data.get("private_key_id"),
            }

            logger.info("Local credentials file validation successful")
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
            # Use the centralized credential loading function
            self.credentials = get_google_credentials()

            # Try to validate the credentials if possible
            try:
                self.validate_credentials_file()
            except Exception as e:
                logger.warning(f"Credential validation warning: {str(e)}")
                # Don't fail authentication if validation has issues
                # as long as we have working credentials

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

            # Try a simple operation to test connectivity
            # List the user's available spreadsheets (limited operation)
            try:
                # This is a lightweight test operation
                client.list_permissions("test_nonexistent_sheet")
            except gspread.exceptions.SpreadsheetNotFound:
                # This is expected - we're just testing auth works
                pass
            except gspread.exceptions.APIError as e:
                if "not found" in str(e).lower():
                    # This is also expected for our test
                    pass
                else:
                    raise e

            # If we get here, authentication worked
            account_email = "Unknown"
            if hasattr(st, "secrets") and "gcp_service_account" in st.secrets:
                account_email = st.secrets["gcp_service_account"].get(
                    "client_email", "Unknown"
                )
            elif self.service_account_info:
                account_email = self.service_account_info.get("client_email", "Unknown")

            success_msg = f"Connection successful! Service account: {account_email}"
            logger.info(success_msg)
            return True, success_msg

        except Exception as e:
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
            try:
                self.validate_credentials_file()
            except Exception as e:
                logger.warning(f"Could not load account info: {str(e)}")
                return {"error": str(e)}

        return self.service_account_info.copy() if self.service_account_info else {}


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

        # Check if we have any valid credential source
        has_secrets = hasattr(st, "secrets") and "gcp_service_account" in st.secrets
        has_local_file = os.path.exists(GOOGLE_CREDENTIALS_PATH)
        has_env_var = bool(os.getenv("GOOGLE_APPLICATION_CREDENTIALS_JSON"))

        if not (has_secrets or has_local_file or has_env_var):
            issues.append(
                "No valid credential source found (secrets, local file, or env var)"
            )

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
