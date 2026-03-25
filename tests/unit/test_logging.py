"""Unit tests for lazy_bird.core.logging module.

Tests structured logging, formatters, correlation IDs, and helper functions.
"""

import json
import logging
import logging.handlers
from unittest.mock import MagicMock, Mock, patch

import pytest

from lazy_bird.core.logging import (
    JSONFormatter,
    TextFormatter,
    clear_correlation_id,
    correlation_id_var,
    get_correlation_id,
    get_logger,
    log_with_context,
    set_correlation_id,
    setup_logging,
)


class TestJSONFormatter:
    """Test JSONFormatter class."""

    def test_basic_format(self):
        """Test basic JSON formatting of a log record."""
        formatter = JSONFormatter()
        record = logging.LogRecord(
            name="test_logger",
            level=logging.INFO,
            pathname="test.py",
            lineno=10,
            msg="Test message",
            args=(),
            exc_info=None,
        )

        output = formatter.format(record)
        data = json.loads(output)

        assert data["level"] == "INFO"
        assert data["logger"] == "test_logger"
        assert data["message"] == "Test message"
        assert "timestamp" in data
        assert data["timestamp"].endswith("Z")

    def test_format_with_correlation_id(self):
        """Test JSON formatting includes correlation ID when set."""
        formatter = JSONFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=10,
            msg="Test",
            args=(),
            exc_info=None,
        )

        token = correlation_id_var.set("req-abc-123")
        try:
            output = formatter.format(record)
            data = json.loads(output)
            assert data["correlation_id"] == "req-abc-123"
        finally:
            correlation_id_var.reset(token)

    def test_format_without_correlation_id(self):
        """Test JSON formatting without correlation ID."""
        formatter = JSONFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=10,
            msg="Test",
            args=(),
            exc_info=None,
        )

        token = correlation_id_var.set(None)
        try:
            output = formatter.format(record)
            data = json.loads(output)
            assert "correlation_id" not in data
        finally:
            correlation_id_var.reset(token)

    def test_format_with_exception(self):
        """Test JSON formatting includes exception info."""
        formatter = JSONFormatter()

        try:
            raise ValueError("test error")
        except ValueError:
            import sys

            exc_info = sys.exc_info()

        record = logging.LogRecord(
            name="test",
            level=logging.ERROR,
            pathname="test.py",
            lineno=10,
            msg="Error occurred",
            args=(),
            exc_info=exc_info,
        )

        output = formatter.format(record)
        data = json.loads(output)

        assert "exception" in data
        assert "ValueError" in data["exception"]
        assert "test error" in data["exception"]

    def test_format_with_extra_fields(self):
        """Test JSON formatting includes extra fields."""
        formatter = JSONFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=10,
            msg="Test",
            args=(),
            exc_info=None,
        )
        record.extra_fields = {"user_id": 123, "action": "login"}

        output = formatter.format(record)
        data = json.loads(output)

        assert data["user_id"] == 123
        assert data["action"] == "login"

    @patch("lazy_bird.core.logging.settings")
    def test_format_with_debug_mode(self, mock_settings):
        """Test JSON formatting includes file info in debug mode."""
        mock_settings.DEBUG = True
        formatter = JSONFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.DEBUG,
            pathname="test.py",
            lineno=42,
            msg="Debug msg",
            args=(),
            exc_info=None,
        )

        output = formatter.format(record)
        data = json.loads(output)

        assert data["file"] == "test.py"
        assert data["line"] == 42
        assert "function" in data


class TestTextFormatter:
    """Test TextFormatter class."""

    def test_basic_format(self):
        """Test basic text formatting."""
        formatter = TextFormatter()
        record = logging.LogRecord(
            name="test_logger",
            level=logging.INFO,
            pathname="test.py",
            lineno=10,
            msg="Test message",
            args=(),
            exc_info=None,
        )

        token = correlation_id_var.set(None)
        try:
            output = formatter.format(record)
            assert "INFO" in output
            assert "test_logger" in output
            assert "Test message" in output
        finally:
            correlation_id_var.reset(token)

    def test_format_with_correlation_id(self):
        """Test text formatting includes correlation ID."""
        formatter = TextFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=10,
            msg="Test",
            args=(),
            exc_info=None,
        )

        token = correlation_id_var.set("req-abcdefgh-1234")
        try:
            output = formatter.format(record)
            assert "req-abcd" in output  # First 8 chars
        finally:
            correlation_id_var.reset(token)

    def test_format_with_exception(self):
        """Test text formatting includes exception info."""
        formatter = TextFormatter()

        try:
            raise RuntimeError("test error")
        except RuntimeError:
            import sys

            exc_info = sys.exc_info()

        record = logging.LogRecord(
            name="test",
            level=logging.ERROR,
            pathname="test.py",
            lineno=10,
            msg="Error",
            args=(),
            exc_info=exc_info,
        )

        output = formatter.format(record)
        assert "RuntimeError" in output
        assert "test error" in output

    def test_color_codes_present(self):
        """Test that color codes are defined for all levels."""
        assert "DEBUG" in TextFormatter.COLORS
        assert "INFO" in TextFormatter.COLORS
        assert "WARNING" in TextFormatter.COLORS
        assert "ERROR" in TextFormatter.COLORS
        assert "CRITICAL" in TextFormatter.COLORS
        assert "RESET" in TextFormatter.COLORS


class TestSetupLogging:
    """Test setup_logging function."""

    @patch("lazy_bird.core.logging.settings")
    def test_setup_logging_text_format(self, mock_settings):
        """Test setup_logging with text format."""
        mock_settings.LOG_LEVEL = "INFO"
        mock_settings.LOG_FORMAT = "text"
        mock_settings.LOG_FILE = None

        setup_logging()

        root_logger = logging.getLogger()
        assert root_logger.level == logging.INFO
        # Should have at least a console handler
        assert len(root_logger.handlers) >= 1

    @patch("lazy_bird.core.logging.settings")
    def test_setup_logging_json_format(self, mock_settings):
        """Test setup_logging with JSON format."""
        mock_settings.LOG_LEVEL = "DEBUG"
        mock_settings.LOG_FORMAT = "json"
        mock_settings.LOG_FILE = None

        setup_logging()

        root_logger = logging.getLogger()
        assert root_logger.level == logging.DEBUG

    @patch("lazy_bird.core.logging.settings")
    def test_setup_logging_with_file(self, mock_settings, tmp_path):
        """Test setup_logging creates file handler."""
        log_file = tmp_path / "test.log"
        mock_settings.LOG_LEVEL = "INFO"
        mock_settings.LOG_FORMAT = "text"
        mock_settings.LOG_FILE = str(log_file)

        setup_logging()

        root_logger = logging.getLogger()
        # Should have console + file handler
        handler_types = [type(h) for h in root_logger.handlers]
        assert logging.handlers.RotatingFileHandler in handler_types

    @patch("lazy_bird.core.logging.settings")
    def test_setup_logging_creates_log_directory(self, mock_settings, tmp_path):
        """Test setup_logging creates parent directory for log file."""
        log_file = tmp_path / "subdir" / "test.log"
        mock_settings.LOG_LEVEL = "INFO"
        mock_settings.LOG_FORMAT = "text"
        mock_settings.LOG_FILE = str(log_file)

        setup_logging()

        assert log_file.parent.exists()

    @patch("lazy_bird.core.logging.settings")
    def test_setup_logging_clears_existing_handlers(self, mock_settings):
        """Test setup_logging removes existing handlers."""
        mock_settings.LOG_LEVEL = "INFO"
        mock_settings.LOG_FORMAT = "text"
        mock_settings.LOG_FILE = None

        root_logger = logging.getLogger()
        root_logger.addHandler(logging.StreamHandler())
        root_logger.addHandler(logging.StreamHandler())
        initial_count = len(root_logger.handlers)

        setup_logging()

        # Should have been cleared and re-added (1 console handler)
        assert len(root_logger.handlers) < initial_count or len(root_logger.handlers) == 1


class TestCorrelationId:
    """Test correlation ID functions."""

    def test_set_and_get_correlation_id(self):
        """Test setting and getting correlation ID."""
        set_correlation_id("test-id-123")
        result = get_correlation_id()
        assert result == "test-id-123"

        # Clean up
        clear_correlation_id()

    def test_clear_correlation_id(self):
        """Test clearing correlation ID."""
        set_correlation_id("test-id-456")
        clear_correlation_id()
        result = get_correlation_id()
        assert result is None

    def test_get_correlation_id_default(self):
        """Test getting correlation ID when not set."""
        clear_correlation_id()
        result = get_correlation_id()
        assert result is None


class TestGetLogger:
    """Test get_logger function."""

    def test_get_logger_returns_logger(self):
        """Test get_logger returns a logging.Logger instance."""
        logger = get_logger("test.module")

        assert isinstance(logger, logging.Logger)
        assert logger.name == "test.module"

    def test_get_logger_same_name_returns_same_logger(self):
        """Test get_logger returns same logger for same name."""
        logger1 = get_logger("test.same")
        logger2 = get_logger("test.same")

        assert logger1 is logger2


class TestLogWithContext:
    """Test log_with_context function."""

    def test_log_with_context_info(self):
        """Test logging with context at INFO level."""
        mock_logger = MagicMock()

        log_with_context(
            mock_logger,
            logging.INFO,
            "Task completed",
            task_id="abc",
            duration=1.5,
        )

        mock_logger.log.assert_called_once_with(
            logging.INFO,
            "Task completed",
            extra={"extra_fields": {"task_id": "abc", "duration": 1.5}},
        )

    def test_log_with_context_error(self):
        """Test logging with context at ERROR level."""
        mock_logger = MagicMock()

        log_with_context(
            mock_logger,
            logging.ERROR,
            "Task failed",
            error="timeout",
        )

        mock_logger.log.assert_called_once_with(
            logging.ERROR,
            "Task failed",
            extra={"extra_fields": {"error": "timeout"}},
        )

    def test_log_with_context_no_extra_fields(self):
        """Test logging with context but no extra fields."""
        mock_logger = MagicMock()

        log_with_context(mock_logger, logging.WARNING, "Simple warning")

        mock_logger.log.assert_called_once_with(
            logging.WARNING,
            "Simple warning",
            extra={"extra_fields": {}},
        )
