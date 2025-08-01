# src/utils/logging_config.py
"""
Simple logging configuration for Medical Schedule Management System.
Provides consistent logging across all modules with proper formatting.
"""

import logging
import os
from datetime import datetime
from pathlib import Path


def setup_logging(log_level: str = "INFO", log_to_file: bool = True) -> logging.Logger:
    """
    Set up logging configuration for the application.

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR)
        log_to_file: Whether to log to file in addition to console

    Returns:
        Configured logger instance
    """
    # Create logs directory if it doesn't exist
    if log_to_file:
        logs_dir = Path("logs")
        logs_dir.mkdir(exist_ok=True)

    # Configure root logger
    logger = logging.getLogger("medical_schedule")
    logger.setLevel(getattr(logging, log_level.upper()))

    # Clear any existing handlers
    logger.handlers.clear()

    # Create formatter
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(funcName)s() - %(message)s"
    )

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(getattr(logging, log_level.upper()))
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # File handler (if enabled)
    if log_to_file:
        log_filename = f"logs/medical_schedule_{datetime.now().strftime('%Y%m%d')}.log"
        file_handler = logging.FileHandler(log_filename)
        file_handler.setLevel(getattr(logging, log_level.upper()))
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    logger.info(f"Logging initialized - Level: {log_level}, File: {log_to_file}")
    return logger


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance for a specific module.

    Args:
        name: Module name (usually __name__)

    Returns:
        Logger instance
    """
    return logging.getLogger(f"medical_schedule.{name}")


def log_function_entry(logger: logging.Logger, func_name: str, **kwargs):
    """
    Log function entry with parameters.

    Args:
        logger: Logger instance
        func_name: Function name
        **kwargs: Function parameters to log
    """
    if kwargs:
        params = ", ".join([f"{k}={v}" for k, v in kwargs.items()])
        logger.debug(f"Entering {func_name}({params})")
    else:
        logger.debug(f"Entering {func_name}()")


def log_function_exit(logger: logging.Logger, func_name: str, result=None):
    """
    Log function exit with result.

    Args:
        logger: Logger instance
        func_name: Function name
        result: Function result to log
    """
    if result is not None:
        logger.debug(f"Exiting {func_name}() -> {result}")
    else:
        logger.debug(f"Exiting {func_name}()")


def log_error_with_context(logger: logging.Logger, error: Exception, context: str = ""):
    """
    Log error with additional context.

    Args:
        logger: Logger instance
        error: Exception that occurred
        context: Additional context about what was happening
    """
    error_msg = f"Error: {str(error)}"
    if context:
        error_msg = f"{context} - {error_msg}"

    logger.error(error_msg, exc_info=True)


# Initialize logging on module import
_main_logger = setup_logging(
    log_level=os.getenv("LOG_LEVEL", "INFO"),
    log_to_file=os.getenv("LOG_TO_FILE", "true").lower() == "true",
)
