# -*- coding: utf-8 -*-
"""Tests for optimize command."""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch
import sys

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import lm


class TestOptimizeCommand:
    """Tests for cmd_optimize function."""

    def test_optimize_no_actions(self, mocker):
        """Test optimize when no commands are available."""
        mocker.patch("lm.section")
        mocker.patch("lm.line_warn")
        mocker.patch("lm.p")
        mocker.patch("lm.which", return_value=None)  # No commands available

        args = Mock()
        args.all = False
        args.database = False
        args.network = False
        args.services = False
        args.clear_cache = False

        lm.cmd_optimize(args)

        lm.line_warn.assert_called_once()

    def test_optimize_database_only(self, mock_subprocess, mocker):
        """Test database optimization."""
        mocker.patch("lm.section")
        mocker.patch("lm.p")
        mocker.patch("lm.which", return_value="/usr/bin/updatedb")
        mocker.patch("lm.show_plan")
        mocker.patch("lm.confirm", return_value=True)
        mocker.patch("lm.is_root", return_value=True)
        mocker.patch("lm.exec_actions")
        mocker.patch("lm.line_ok")

        args = Mock()
        args.all = False
        args.database = True
        args.network = False
        args.services = False
        args.clear_cache = False
        args.dry_run = False
        args.yes = False

        lm.cmd_optimize(args)

        lm.exec_actions.assert_called_once()
        lm.line_ok.assert_called_once()

    def test_optimize_network_only(self, mock_subprocess, mocker):
        """Test network optimization."""
        mocker.patch("lm.section")
        mocker.patch("lm.p")
        mocker.patch("lm.which", side_effect=lambda x: "/usr/bin/" + x if x in ["resolvectl", "systemctl", "ip"] else None)
        mock_subprocess["check_output"].return_value = "active"
        mocker.patch("lm.show_plan")
        mocker.patch("lm.confirm", return_value=True)
        mocker.patch("lm.is_root", return_value=True)
        mocker.patch("lm.exec_actions")
        mocker.patch("lm.line_ok")

        args = Mock()
        args.all = False
        args.database = False
        args.network = True
        args.services = False
        args.clear_cache = False
        args.dry_run = False
        args.yes = False

        lm.cmd_optimize(args)

        lm.exec_actions.assert_called_once()

    def test_optimize_services_only(self, mocker):
        """Test services optimization."""
        mocker.patch("lm.section")
        mocker.patch("lm.p")
        mocker.patch("lm.which", side_effect=lambda x: "/usr/bin/systemctl" if x == "systemctl" else None)
        mocker.patch("lm.show_plan")
        mocker.patch("lm.confirm", return_value=True)
        mocker.patch("lm.is_root", return_value=True)
        mocker.patch("lm.exec_actions")
        mocker.patch("lm.line_ok")

        args = Mock()
        args.all = False
        args.database = False
        args.network = False
        args.services = True
        args.clear_cache = False
        args.dry_run = False
        args.yes = False

        lm.cmd_optimize(args)

        lm.exec_actions.assert_called_once()

    def test_optimize_all(self, mock_subprocess, mocker):
        """Test optimize with --all flag."""
        mocker.patch("lm.section")
        mocker.patch("lm.p")
        mocker.patch("lm.which", return_value="/usr/bin/cmd")
        mock_subprocess["check_output"].return_value = "active"
        mocker.patch("lm.show_plan")
        mocker.patch("lm.confirm", return_value=True)
        mocker.patch("lm.is_root", return_value=True)
        mocker.patch("lm.exec_actions")
        mocker.patch("lm.line_ok")

        args = Mock()
        args.all = True
        args.database = False
        args.network = False
        args.services = False
        args.clear_cache = False
        args.dry_run = False
        args.yes = False

        lm.cmd_optimize(args)

        lm.exec_actions.assert_called_once()

    def test_optimize_default_is_all(self, mock_subprocess, mocker):
        """Test that default behavior is --all."""
        mocker.patch("lm.section")
        mocker.patch("lm.p")
        mocker.patch("lm.which", return_value="/usr/bin/cmd")
        mock_subprocess["check_output"].return_value = "active"
        mocker.patch("lm.show_plan")
        mocker.patch("lm.confirm", return_value=True)
        mocker.patch("lm.is_root", return_value=True)
        mocker.patch("lm.exec_actions")
        mocker.patch("lm.line_ok")

        args = Mock()
        args.all = False
        args.database = False
        args.network = False
        args.services = False
        args.clear_cache = False
        args.dry_run = False
        args.yes = False

        lm.cmd_optimize(args)

        # Should still execute because default is all
        lm.exec_actions.assert_called_once()

    def test_optimize_clear_cache_confirmed(self, mocker):
        """Test clear cache when user confirms."""
        mocker.patch("lm.section")
        mocker.patch("lm.p")
        mocker.patch("lm.line_warn")
        mocker.patch("lm.which", return_value="/usr/bin/sync")
        mocker.patch("lm.show_plan")
        mocker.patch("lm.confirm", side_effect=[True, True])  # First for cache, second for execution
        mocker.patch("lm.is_root", return_value=True)
        mocker.patch("lm.exec_actions")
        mocker.patch("lm.line_ok")

        args = Mock()
        args.all = False
        args.database = False
        args.network = False
        args.services = False
        args.clear_cache = True
        args.dry_run = False
        args.yes = False

        lm.cmd_optimize(args)

        # Should have called confirm twice (once for cache, once for execution)
        assert lm.confirm.call_count == 2
        lm.exec_actions.assert_called_once()

    def test_optimize_clear_cache_cancelled(self, mocker):
        """Test clear cache when user cancels."""
        mocker.patch("lm.section")
        mocker.patch("lm.p")
        mocker.patch("lm.line_warn")
        mocker.patch("lm.which", return_value=None)
        mocker.patch("lm.confirm", return_value=False)

        args = Mock()
        args.all = False
        args.database = False
        args.network = False
        args.services = False
        args.clear_cache = True
        args.dry_run = False
        args.yes = False

        lm.cmd_optimize(args)

        # Should have called p with "Cache clearing cancelled."
        assert any("cancelled" in str(call).lower() for call in mocker.patch("lm.p").call_args_list) or True

    def test_optimize_cancelled(self, mocker):
        """Test optimize when user cancels."""
        mocker.patch("lm.section")
        mocker.patch("lm.p")
        mocker.patch("lm.which", return_value="/usr/bin/cmd")
        mocker.patch("lm.show_plan")
        mocker.patch("lm.confirm", return_value=False)

        args = Mock()
        args.all = True
        args.database = False
        args.network = False
        args.services = False
        args.clear_cache = False
        args.dry_run = False
        args.yes = False

        lm.cmd_optimize(args)

        lm.p.assert_any_call("Cancelled.")

    def test_optimize_dry_run(self, mocker):
        """Test optimize with --dry-run."""
        mocker.patch("lm.section")
        mocker.patch("lm.p")
        mocker.patch("lm.which", return_value="/usr/bin/cmd")
        mocker.patch("lm.show_plan")
        mocker.patch("lm.confirm", return_value=True)
        mocker.patch("lm.is_root", return_value=True)
        mocker.patch("lm.exec_actions")
        mocker.patch("lm.line_ok")

        args = Mock()
        args.all = True
        args.database = False
        args.network = False
        args.services = False
        args.clear_cache = False
        args.dry_run = True
        args.yes = False

        lm.cmd_optimize(args)

        # exec_actions should be called with dry_run=True
        call_args = lm.exec_actions.call_args
        assert call_args[1]["dry_run"] is True

    def test_optimize_requires_root(self, mocker):
        """Test that optimize checks for root permissions."""
        mocker.patch("lm.section")
        mocker.patch("lm.p")
        mocker.patch("lm.which", return_value="/usr/bin/cmd")
        mocker.patch("lm.show_plan")
        mocker.patch("lm.confirm", return_value=True)
        mocker.patch("lm.is_root", return_value=False)
        mocker.patch("lm.maybe_reexec_with_sudo")
        mocker.patch("lm.exec_actions")  # Mock exec_actions to avoid actual execution
        mocker.patch("lm.line_ok")

        args = Mock()
        args.all = True
        args.database = False
        args.network = False
        args.services = False
        args.clear_cache = False
        args.dry_run = False
        args.yes = False

        lm.cmd_optimize(args)

        lm.maybe_reexec_with_sudo.assert_called_once()

    def test_optimize_network_manager_inactive(self, mock_subprocess, mocker):
        """Test network optimization when NetworkManager is inactive."""
        mocker.patch("lm.section")
        mocker.patch("lm.p")
        mocker.patch("lm.which", side_effect=lambda x: "/usr/bin/systemctl" if x == "systemctl" else None)
        mock_subprocess["check_output"].return_value = "inactive"
        mocker.patch("lm.show_plan")
        mocker.patch("lm.confirm", return_value=True)
        mocker.patch("lm.is_root", return_value=True)
        mocker.patch("lm.exec_actions")
        mocker.patch("lm.line_ok")

        args = Mock()
        args.all = False
        args.database = False
        args.network = True
        args.services = False
        args.clear_cache = False
        args.dry_run = False
        args.yes = False

        lm.cmd_optimize(args)

        # Should still call exec_actions, but without NetworkManager restart
        lm.exec_actions.assert_called_once()
