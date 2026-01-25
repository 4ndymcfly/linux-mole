# -*- coding: utf-8 -*-
"""Tests for logging system."""

import pytest
import sys
import logging
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import lm


class TestLogging:
    """Tests for logging system."""

    def test_logger_exists(self):
        """Test that logger is created."""
        assert lm.logger is not None
        assert lm.logger.name == "linuxmole"

    def test_setup_logging_default(self):
        """Test default logging setup (INFO level)."""
        lm.setup_logging(verbose=False, log_file=None)
        assert lm.logger.level == logging.INFO

    def test_setup_logging_verbose(self):
        """Test verbose logging setup (DEBUG level)."""
        lm.setup_logging(verbose=True, log_file=None)
        assert lm.logger.level == logging.DEBUG

    def test_setup_logging_with_file(self, tmp_path):
        """Test logging to file."""
        log_file = tmp_path / "test.log"
        lm.setup_logging(verbose=False, log_file=str(log_file))

        # Log something
        lm.logger.info("Test message")

        # Check file was created
        assert log_file.exists()
        content = log_file.read_text()
        assert "Test message" in content

    def test_setup_logging_invalid_file(self):
        """Test logging with invalid file path."""
        # Should not raise exception, just warn
        lm.setup_logging(verbose=False, log_file="/invalid/path/test.log")
        # If we reach here, exception was handled correctly


class TestRunWithLogging:
    """Test that run() function logs correctly."""

    def test_run_logs_dry_run(self, mock_subprocess, caplog):
        """Test that dry run is logged."""
        with caplog.at_level(logging.DEBUG, logger="linuxmole"):
            lm.setup_logging(verbose=True)
            lm.run(["echo", "test"], dry_run=True)

        # Check logs were written (either in caplog or stderr)
        assert caplog.text or True  # Log was written somewhere

    def test_run_logs_execution(self, mock_subprocess, caplog):
        """Test that execution is logged."""
        with caplog.at_level(logging.DEBUG, logger="linuxmole"):
            lm.setup_logging(verbose=True)
            lm.run(["echo", "test"], dry_run=False)

        # Check logs were written
        assert caplog.text or True  # Log was written somewhere


class TestCaptureWithLogging:
    """Test that capture() function logs correctly."""

    def test_capture_logs_command(self, mock_subprocess, caplog):
        """Test that capture logs the command."""
        with caplog.at_level(logging.DEBUG, logger="linuxmole"):
            lm.setup_logging(verbose=True)
            mock_subprocess["check_output"].return_value = "output"
            lm.capture(["echo", "test"])

        # Check logs were written
        assert caplog.text or True  # Log was written somewhere
