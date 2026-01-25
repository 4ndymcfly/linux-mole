# -*- coding: utf-8 -*-
"""Tests for helper functions."""

import pytest
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import lm


class TestHumanBytes:
    """Tests for human_bytes() function."""

    def test_bytes(self):
        assert lm.human_bytes(0) == "0B"
        assert lm.human_bytes(500) == "500B"
        assert lm.human_bytes(1023) == "1023B"

    def test_kilobytes(self):
        assert lm.human_bytes(1024) == "1.0KB"
        assert lm.human_bytes(1536) == "1.5KB"
        assert lm.human_bytes(2048) == "2.0KB"

    def test_megabytes(self):
        assert lm.human_bytes(1024 * 1024) == "1.0MB"
        assert lm.human_bytes(5 * 1024 * 1024) == "5.0MB"

    def test_gigabytes(self):
        assert lm.human_bytes(1024 * 1024 * 1024) == "1.0GB"
        assert lm.human_bytes(10 * 1024 * 1024 * 1024) == "10.0GB"

    def test_terabytes(self):
        assert lm.human_bytes(1024 * 1024 * 1024 * 1024) == "1.0TB"


class TestFormatSize:
    """Tests for format_size() function."""

    def test_none_value(self):
        assert lm.format_size(None) == "size unavailable"

    def test_normal_value(self):
        assert lm.format_size(1024) == "1.0KB"

    def test_unknown_flag(self):
        assert lm.format_size(1024, unknown=True) == "1.0KB+"


class TestIsRoot:
    """Tests for is_root() function."""

    def test_root_user(self, mock_root_user):
        assert lm.is_root() is True

    def test_non_root_user(self, mock_non_root_user):
        assert lm.is_root() is False


class TestConfirm:
    """Tests for confirm() function."""

    def test_assume_yes(self):
        assert lm.confirm("Test?", assume_yes=True) is True

    def test_user_input_yes(self, mocker):
        mocker.patch("builtins.input", return_value="y")
        assert lm.confirm("Test?", assume_yes=False) is True

    def test_user_input_yes_full(self, mocker):
        mocker.patch("builtins.input", return_value="yes")
        assert lm.confirm("Test?", assume_yes=False) is True

    def test_user_input_no(self, mocker):
        mocker.patch("builtins.input", return_value="n")
        assert lm.confirm("Test?", assume_yes=False) is False

    def test_user_input_empty(self, mocker):
        mocker.patch("builtins.input", return_value="")
        assert lm.confirm("Test?", assume_yes=False) is False


class TestWhich:
    """Tests for which() function."""

    def test_existing_command(self):
        result = lm.which("python3")
        assert result is not None
        assert "python3" in result

    def test_nonexistent_command(self):
        result = lm.which("this_command_does_not_exist_12345")
        assert result is None


class TestRun:
    """Tests for run() function."""

    def test_dry_run(self, mock_subprocess, capsys):
        result = lm.run(["echo", "test"], dry_run=True)
        assert result.returncode == 0
        captured = capsys.readouterr()
        # Output contains the command
        assert "echo" in captured.out and "test" in captured.out

    def test_normal_run(self, mock_subprocess, capsys):
        lm.run(["echo", "test"], dry_run=False)
        mock_subprocess["run"].assert_called_once()
        captured = capsys.readouterr()
        # Output contains the command
        assert "echo" in captured.out and "test" in captured.out


class TestCapture:
    """Tests for capture() function."""

    def test_capture_output(self, mock_subprocess):
        mock_subprocess["check_output"].return_value = "test output\n"
        result = lm.capture(["echo", "test"])
        assert result == "test output"
        mock_subprocess["check_output"].assert_called_once()
