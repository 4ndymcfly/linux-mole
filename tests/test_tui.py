# -*- coding: utf-8 -*-
"""Tests for TUI (analyze --tui) functionality."""

import pytest
import subprocess
from pathlib import Path
from unittest.mock import Mock, patch
import sys

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import lm


class TestAnalyzeTUI:
    """Tests for analyze command with TUI."""

    def test_analyze_without_tui(self, mock_subprocess, mocker):
        """Test analyze command without --tui flag (table mode)."""
        mocker.patch("lm.section")
        mocker.patch("lm.table")
        mocker.patch("lm.which", return_value="/usr/bin/du")
        mock_subprocess["check_output"].return_value = "1024\t/tmp/file1\n2048\t/tmp/file2\n"

        args = Mock()
        args.path = "/tmp"
        args.top = 10
        args.tui = False

        lm.cmd_analyze(args)

        # Should show table
        lm.table.assert_called_once()

    def test_analyze_tui_not_available_user_declines_install(self, mocker):
        """Test analyze --tui when textual is not available and user declines installation."""
        mocker.patch("lm.TEXTUAL", False)
        mocker.patch("lm.line_warn")
        mocker.patch("lm.p")
        mocker.patch("lm.confirm", return_value=False)  # User declines
        mocker.patch("lm.section")
        mocker.patch("lm.table")
        mocker.patch("lm.which", return_value="/usr/bin/du")
        mocker.patch("lm.capture", return_value="1024\t/tmp/file1\n")

        args = Mock()
        args.path = "/tmp"
        args.top = 10
        args.tui = True

        lm.cmd_analyze(args)

        # Should ask for confirmation
        lm.confirm.assert_called_once()
        # Should show warning and fallback to table
        lm.line_warn.assert_called()

    def test_analyze_tui_not_available_user_accepts_install_success(self, mocker):
        """Test analyze --tui when user accepts installation and it succeeds."""
        mocker.patch("lm.TEXTUAL", False)
        mocker.patch("lm.line_warn")
        mocker.patch("lm.line_ok")
        mocker.patch("lm.p")
        mocker.patch("lm.confirm", return_value=True)  # User accepts

        # Mock successful subprocess.run
        mock_result = Mock()
        mock_result.returncode = 0
        mock_subprocess_run = mocker.patch("subprocess.run", return_value=mock_result)

        args = Mock()
        args.path = "/tmp"
        args.top = 10
        args.tui = True

        lm.cmd_analyze(args)

        # Should have tried to install
        mock_subprocess_run.assert_called_once()
        # Should show success message
        lm.line_ok.assert_called()

    def test_analyze_tui_not_available_user_accepts_install_fails(self, mocker):
        """Test analyze --tui when user accepts installation but it fails."""
        mocker.patch("lm.TEXTUAL", False)
        mocker.patch("lm.line_warn")
        mocker.patch("lm.p")
        mocker.patch("lm.confirm", return_value=True)  # User accepts

        # Mock failed subprocess.run
        mock_result = Mock()
        mock_result.returncode = 1
        mock_result.stderr = "Installation failed"
        mocker.patch("subprocess.run", return_value=mock_result)

        mocker.patch("lm.section")
        mocker.patch("lm.table")
        mocker.patch("lm.which", return_value="/usr/bin/du")
        mocker.patch("lm.capture", return_value="1024\t/tmp/file1\n")

        args = Mock()
        args.path = "/tmp"
        args.top = 10
        args.tui = True

        lm.cmd_analyze(args)

        # Should show failure and fallback
        assert any("Failed to install" in str(call) for call in lm.line_warn.call_args_list)
        # Should fallback to table
        lm.table.assert_called_once()

    def test_analyze_tui_not_available_install_timeout(self, mocker):
        """Test analyze --tui when installation times out."""
        mocker.patch("lm.TEXTUAL", False)
        mocker.patch("lm.line_warn")
        mocker.patch("lm.p")
        mocker.patch("lm.confirm", return_value=True)  # User accepts

        # Mock timeout
        mocker.patch("subprocess.run", side_effect=subprocess.TimeoutExpired("pip", 60))

        mocker.patch("lm.section")
        mocker.patch("lm.table")
        mocker.patch("lm.which", return_value="/usr/bin/du")
        mocker.patch("lm.capture", return_value="1024\t/tmp/file1\n")

        args = Mock()
        args.path = "/tmp"
        args.top = 10
        args.tui = True

        lm.cmd_analyze(args)

        # Should show timeout warning
        assert any("timed out" in str(call).lower() for call in lm.line_warn.call_args_list)
        # Should fallback to table
        lm.table.assert_called_once()

    @pytest.mark.skipif(not lm.TEXTUAL, reason="Textual not available")
    def test_analyze_tui_available(self, mocker):
        """Test analyze --tui when textual is available."""
        mock_app = Mock()
        mocker.patch("lm.DiskAnalyzerApp", return_value=mock_app)

        args = Mock()
        args.path = "/tmp"
        args.top = 10
        args.tui = True

        lm.cmd_analyze(args)

        # Should create and run app
        lm.DiskAnalyzerApp.assert_called_once_with(start_path="/tmp")
        mock_app.run.assert_called_once()

    def test_analyze_table_mode_sorts_by_size(self, mock_subprocess, mocker):
        """Test that table mode sorts entries by size."""
        mocker.patch("lm.section")
        mocker.patch("lm.table")
        mocker.patch("lm.which", return_value="/usr/bin/du")

        # Mock du output with different sizes
        du_output = "1024\t/tmp/small\n4096\t/tmp/large\n2048\t/tmp/medium\n"
        mock_subprocess["check_output"].return_value = du_output

        args = Mock()
        args.path = "/tmp"
        args.top = 10
        args.tui = False

        lm.cmd_analyze(args)

        # Verify table was called
        lm.table.assert_called_once()
        call_args = lm.table.call_args[0]

        # Check that rows are sorted by size (largest first)
        rows = call_args[2]  # Third argument is rows
        # First row should be 'large' (4096 bytes)
        assert "large" in rows[0][2]  # Name column

    def test_analyze_respects_top_limit(self, mock_subprocess, mocker):
        """Test that analyze respects --top limit."""
        mocker.patch("lm.section")
        mocker.patch("lm.table")
        mocker.patch("lm.which", return_value="/usr/bin/du")

        # Mock du output with 5 entries
        du_output = "\n".join([f"{i*1024}\t/tmp/file{i}" for i in range(1, 6)])
        mock_subprocess["check_output"].return_value = du_output

        args = Mock()
        args.path = "/tmp"
        args.top = 3
        args.tui = False

        lm.cmd_analyze(args)

        # Verify table was called with max 3 rows
        lm.table.assert_called_once()
        call_args = lm.table.call_args[0]
        rows = call_args[2]
        assert len(rows) <= 3

    def test_analyze_handles_empty_directory(self, mock_subprocess, mocker):
        """Test analyze with empty directory."""
        mocker.patch("lm.section")
        mocker.patch("lm.line_warn")
        mocker.patch("lm.which", return_value="/usr/bin/du")
        mock_subprocess["check_output"].return_value = ""

        args = Mock()
        args.path = "/tmp/empty"
        args.top = 10
        args.tui = False

        lm.cmd_analyze(args)

        # Should show warning
        lm.line_warn.assert_called_once_with("Unable to analyze path")

    def test_analyze_handles_du_not_found(self, mocker):
        """Test analyze when du command is not available."""
        mocker.patch("lm.section")
        mocker.patch("lm.line_warn")
        mocker.patch("lm.which", return_value=None)

        args = Mock()
        args.path = "/tmp"
        args.top = 10
        args.tui = False

        lm.cmd_analyze(args)

        # Should show warning
        lm.line_warn.assert_called_once_with("Unable to analyze path")

    def test_analyze_expands_tilde_path(self, mock_subprocess, mocker):
        """Test that analyze expands ~ in path."""
        mocker.patch("lm.section")
        mocker.patch("lm.table")
        mocker.patch("lm.which", return_value="/usr/bin/du")
        mock_subprocess["check_output"].return_value = "1024\t/home/user/file\n"
        mock_expanduser = mocker.patch("os.path.expanduser", return_value="/home/user")

        args = Mock()
        args.path = "~"
        args.top = 10
        args.tui = False

        lm.cmd_analyze(args)

        # Should have expanded ~
        mock_expanduser.assert_called_once_with("~")


@pytest.mark.skipif(not lm.TEXTUAL, reason="Textual not available")
class TestDiskAnalyzerApp:
    """Tests for DiskAnalyzerApp TUI class."""

    def test_app_initialization(self):
        """Test TUI app can be initialized."""
        app = lm.DiskAnalyzerApp(start_path="/tmp")
        assert app.start_path == "/tmp"
        assert app.total_size == 0

    def test_app_has_bindings(self):
        """Test TUI app has expected keybindings."""
        app = lm.DiskAnalyzerApp(start_path="/tmp")

        # Check that bindings exist
        # BINDINGS can be Binding objects or tuples
        binding_keys = []
        for b in app.BINDINGS:
            if hasattr(b, 'key'):
                binding_keys.append(b.key)
            elif isinstance(b, tuple) and len(b) > 0:
                binding_keys.append(b[0])

        assert "q" in binding_keys  # Quit
        assert "r" in binding_keys  # Refresh

    def test_app_title(self):
        """Test TUI app has correct title."""
        app = lm.DiskAnalyzerApp(start_path="/tmp")
        assert "LinuxMole" in app.TITLE
        assert "Disk Usage" in app.TITLE


@pytest.mark.skipif(not lm.TEXTUAL, reason="Textual not available")
class TestDiskUsageInfo:
    """Tests for DiskUsageInfo widget."""

    def test_widget_empty_render(self):
        """Test widget renders empty state."""
        widget = lm.DiskUsageInfo()
        output = widget.render()
        assert "Select a directory" in output

    def test_widget_with_data(self):
        """Test widget renders with data."""
        widget = lm.DiskUsageInfo()
        widget.path = "/tmp/test"
        widget.size = 1024 * 1024  # 1 MB
        widget.total_size = 1024 * 1024 * 10  # 10 MB

        output = widget.render()
        assert "/tmp/test" in output
        # Check for size (format_size may output MB, MiB, etc)
        assert ("MB" in output or "MiB" in output or "KiB" in output)
        assert "10.0%" in output  # Percentage
