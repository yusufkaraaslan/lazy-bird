"""Structured logging configuration for Lazy-Bird.

This module sets up structured logging with JSON formatting, correlation IDs,
and both console and file handlers.
"""

import logging
import logging.handlers
import sys
from contextvars import ContextVar
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from lazy_bird.core.config import settings

# Context variable for request correlation ID
correlation_id_var: ContextVar[Optional[str]] = ContextVar("correlation_id", default=None)


class JSONFormatter(logging.Formatter):
    """JSON log formatter with correlation ID support.

    Formats log records as JSON for structured logging.
    Includes correlation ID from context if available.
    """

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON.

        Args:
            record: Log record to format

        Returns:
            str: JSON-formatted log entry
        """
        import json

        # Base log data
        log_data: Dict[str, Any] = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Add correlation ID if available
        correlation_id = correlation_id_var.get()
        if correlation_id:
            log_data["correlation_id"] = correlation_id

        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        # Add extra fields from record
        if hasattr(record, "extra_fields"):
            log_data.update(record.extra_fields)

        # Add file/function/line info for debugging
        if settings.DEBUG:
            log_data["file"] = record.filename
            log_data["function"] = record.funcName
            log_data["line"] = record.lineno

        return json.dumps(log_data, default=str)


class TextFormatter(logging.Formatter):
    """Human-readable text formatter with correlation ID support.

    Formats log records as colored text for console output.
    """

    # ANSI color codes
    COLORS = {
        "DEBUG": "\033[36m",  # Cyan
        "INFO": "\033[32m",  # Green
        "WARNING": "\033[33m",  # Yellow
        "ERROR": "\033[31m",  # Red
        "CRITICAL": "\033[35m",  # Magenta
        "RESET": "\033[0m",  # Reset
    }

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as colored text.

        Args:
            record: Log record to format

        Returns:
            str: Formatted log entry with color codes
        """
        # Get color for log level
        color = self.COLORS.get(record.levelname, self.COLORS["RESET"])
        reset = self.COLORS["RESET"]

        # Base format
        timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        level = f"{color}{record.levelname:8}{reset}"
        logger = f"{record.name:20}"
        message = record.getMessage()

        # Add correlation ID if available
        correlation_id = correlation_id_var.get()
        if correlation_id:
            log_str = f"{timestamp} | {level} | {logger} | [{correlation_id[:8]}] | {message}"
        else:
            log_str = f"{timestamp} | {level} | {logger} | {message}"

        # Add exception info if present
        if record.exc_info:
            log_str += "\n" + self.formatException(record.exc_info)

        return log_str


def setup_logging() -> None:
    """Configure application logging.

    Sets up logging based on settings:
    - Log level from settings.LOG_LEVEL
    - Format from settings.LOG_FORMAT (json or text)
    - Optional file logging from settings.LOG_FILE
    - Console logging to stderr

    This should be called once at application startup.
    """
    # Get root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, settings.LOG_LEVEL))

    # Remove existing handlers
    root_logger.handlers.clear()

    # Choose formatter based on settings
    if settings.LOG_FORMAT == "json":
        formatter = JSONFormatter()
    else:
        formatter = TextFormatter()

    # Console handler (stderr)
    console_handler = logging.StreamHandler(sys.stderr)
    console_handler.setLevel(getattr(logging, settings.LOG_LEVEL))
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # File handler (if configured)
    if settings.LOG_FILE:
        log_file = Path(settings.LOG_FILE)
        log_file.parent.mkdir(parents=True, exist_ok=True)

        # Use rotating file handler (10MB max, 5 backups)
        file_handler = logging.handlers.RotatingFileHandler(
            filename=log_file,
            maxBytes=10 * 1024 * 1024,  # 10 MB
            backupCount=5,
            encoding="utf-8",
        )
        file_handler.setLevel(getattr(logging, settings.LOG_LEVEL))
        file_handler.setFormatter(JSONFormatter())  # Always use JSON for files
        root_logger.addHandler(file_handler)

    # Configure third-party library logging
    logging.getLogger("uvicorn").setLevel(logging.INFO)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy").setLevel(logging.WARNING)
    logging.getLogger("alembic").setLevel(logging.INFO)

    # Log startup message
    logger = logging.getLogger(__name__)
    logger.info(
        "Logging configured",
        extra={
            "extra_fields": {
                "log_level": settings.LOG_LEVEL,
                "log_format": settings.LOG_FORMAT,
                "log_file": str(settings.LOG_FILE) if settings.LOG_FILE else None,
            }
        },
    )


def set_correlation_id(correlation_id: str) -> None:
    """Set correlation ID for current context.

    Args:
        correlation_id: Unique request/task identifier

    Example:
        >>> set_correlation_id("req-abc123")
        >>> logger.info("Processing request")
        # Log will include correlation_id: req-abc123
    """
    correlation_id_var.set(correlation_id)


def clear_correlation_id() -> None:
    """Clear correlation ID from current context."""
    correlation_id_var.set(None)


def get_correlation_id() -> Optional[str]:
    """Get current correlation ID.

    Returns:
        Optional[str]: Correlation ID or None if not set
    """
    return correlation_id_var.get()


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance for a module.

    Args:
        name: Logger name (usually __name__)

    Returns:
        logging.Logger: Configured logger instance

    Example:
        >>> logger = get_logger(__name__)
        >>> logger.info("Operation completed", extra={"extra_fields": {"user_id": 123}})
    """
    return logging.getLogger(name)


# Convenience function for logging with extra fields
def log_with_context(
    logger: logging.Logger,
    level: int,
    message: str,
    **extra_fields: Any,
) -> None:
    """Log message with extra fields.

    Args:
        logger: Logger instance
        level: Log level (logging.INFO, logging.ERROR, etc.)
        message: Log message
        **extra_fields: Additional fields to include in log

    Example:
        >>> logger = get_logger(__name__)
        >>> log_with_context(logger, logging.INFO, "Task completed", task_id="abc", duration=1.5)
    """
    logger.log(level, message, extra={"extra_fields": extra_fields})
