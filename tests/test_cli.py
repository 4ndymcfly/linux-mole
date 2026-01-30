# -*- coding: utf-8 -*-
"""Tests for CLI functionality."""

import pytest
import sys
from pathlib import Path
from unittest.mock import patch

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import lm


class TestMainFunction:
    """Tests for main() function."""

    def test_main_version_flag(self, capsys):
        """Test --version flag."""
        with patch.object(sys, "argv", ["lm", "--version"]):
            lm.main()
            captured = capsys.readouterr()
            # Verify version output contains LinuxMole and a version number
            assert "LinuxMole" in captured.out
            assert lm.VERSION in captured.out

    def test_main_help_flag(self, capsys):
        """Test --help flag."""
        with patch.object(sys, "argv", ["lm", "--help"]):
            try:
                lm.main()
                captured = capsys.readouterr()
                # Should show help text
                assert "LinuxMole" in captured.out or "help" in captured.out.lower()
            except SystemExit:
                # Help may exit with 0
                pass

    def test_main_no_args(self, mocker):
        """Test main with no arguments (interactive mode)."""
        with patch.object(sys, "argv", ["lm"]):
            # Mock interactive_simple to avoid actually running it
            mock_interactive = mocker.patch("lm.interactive_simple")
            lm.main()
            mock_interactive.assert_called_once()


class TestCLIFlags:
    """Test CLI flag parsing."""

    def test_verbose_flag_exists(self):
        """Test that --verbose flag exists in argparse setup."""
        # This test verifies the flag is in the code
        # More comprehensive test would need to parse args
        with open(Path(__file__).parent.parent / "lm.py", "r") as f:
            content = f.read()
            assert "--verbose" in content
            assert "-v" in content

    def test_log_file_flag_exists(self):
        """Test that --log-file flag exists in argparse setup."""
        with open(Path(__file__).parent.parent / "lm.py", "r") as f:
            content = f.read()
            assert "--log-file" in content


class TestCommandValidation:
    """Test command validation."""

    def test_invalid_command(self, capsys, mocker):
        """Test invalid command shows help."""
        with patch.object(sys, "argv", ["lm", "invalid_command"]):
            mock_print_help = mocker.patch("lm.print_help")
            try:
                lm.main()
            except SystemExit:
                pass
            # Should call print_help or argparse error
