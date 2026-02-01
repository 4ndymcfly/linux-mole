#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests for enhanced interactive menu functions.
"""

import pytest
from unittest.mock import patch, MagicMock, call
import argparse

from linuxmole.interactive import (
    simple_analyze,
    simple_purge,
    simple_installer,
    simple_uninstall,
    simple_optimize,
    simple_whitelist,
    simple_config,
    simple_update,
    simple_self_uninstall,
    print_category_header,
    print_submenu_header,
    print_mode_banner
)


# ══════════════════════════════════════════════════════════════
# Helper Function Tests
# ══════════════════════════════════════════════════════════════

def test_print_category_header(capsys):
    """Test category header printing."""
    print_category_header("📊", "TEST CATEGORY")
    captured = capsys.readouterr()
    assert "📊" in captured.out
    assert "TEST CATEGORY" in captured.out


def test_print_submenu_header(capsys):
    """Test submenu header printing."""
    print_submenu_header("TEST MENU")
    captured = capsys.readouterr()
    assert "TEST MENU" in captured.out


def test_print_mode_banner_normal(capsys):
    """Test mode banner in normal mode."""
    with patch('linuxmole.interactive.is_root', return_value=False):
        print_mode_banner(dry_run_mode=False)
        captured = capsys.readouterr()
        assert "NORMAL MODE" in captured.out


def test_print_mode_banner_dry_run(capsys):
    """Test mode banner in dry-run mode."""
    with patch('linuxmole.interactive.is_root', return_value=True):
        print_mode_banner(dry_run_mode=True)
        captured = capsys.readouterr()
        assert "DRY-RUN MODE" in captured.out


def test_print_mode_banner_root(capsys):
    """Test mode banner in root mode."""
    with patch('linuxmole.interactive.is_root', return_value=True):
        print_mode_banner(dry_run_mode=False)
        captured = capsys.readouterr()
        assert "ROOT MODE" in captured.out


# ══════════════════════════════════════════════════════════════
# Wizard Function Tests - Basic
# ══════════════════════════════════════════════════════════════

@patch('linuxmole.interactive.cmd_analyze')
@patch('linuxmole.interactive.input')
@patch('linuxmole.interactive.prompt_bool')
def test_simple_analyze_defaults(mock_prompt, mock_input, mock_cmd):
    """Test analyze wizard with defaults."""
    mock_input.side_effect = ["", ""]  # Use defaults for path and top
    mock_prompt.return_value = True  # Use TUI

    simple_analyze()

    mock_cmd.assert_called_once()
    args = mock_cmd.call_args[0][0]
    assert args.path == "/"
    assert args.top == 10
    assert args.tui is True


@patch('linuxmole.interactive.cmd_analyze')
@patch('linuxmole.interactive.input')
@patch('linuxmole.interactive.prompt_bool')
def test_simple_analyze_custom(mock_prompt, mock_input, mock_cmd):
    """Test analyze wizard with custom values."""
    mock_input.side_effect = ["/home", "20"]
    mock_prompt.return_value = False  # Don't use TUI

    simple_analyze()

    args = mock_cmd.call_args[0][0]
    assert args.path == "/home"
    assert args.top == 20
    assert args.tui is False


@patch('linuxmole.interactive.cmd_purge')
@patch('linuxmole.interactive.input')
@patch('linuxmole.interactive.prompt_bool')
def test_simple_purge(mock_prompt, mock_input, mock_cmd):
    """Test purge wizard."""
    mock_input.return_value = "/home/user"
    mock_prompt.return_value = True  # dry_run=True

    simple_purge()

    mock_cmd.assert_called_once()
    args = mock_cmd.call_args[0][0]
    assert args.path == "/home/user"
    assert args.dry_run is True


@patch('linuxmole.interactive.cmd_installer')
@patch('linuxmole.interactive.input')
@patch('linuxmole.interactive.prompt_bool')
def test_simple_installer(mock_prompt, mock_input, mock_cmd):
    """Test installer wizard."""
    mock_input.return_value = "~"
    mock_prompt.return_value = True  # dry_run=True

    simple_installer()

    mock_cmd.assert_called_once()
    args = mock_cmd.call_args[0][0]
    assert args.path == "~"
    assert args.dry_run is True


# ══════════════════════════════════════════════════════════════
# Wizard Function Tests - Advanced
# ══════════════════════════════════════════════════════════════

@patch('linuxmole.interactive.cmd_uninstall_app')
@patch('linuxmole.interactive.input')
@patch('linuxmole.interactive.prompt_bool')
@patch('linuxmole.interactive.pause')
def test_simple_uninstall_package(mock_pause, mock_prompt, mock_input, mock_cmd):
    """Test uninstall wizard - package removal."""
    mock_input.side_effect = ["1", "firefox"]  # Option 1, package name
    mock_prompt.side_effect = [True, True]  # purge=True, dry_run=True

    simple_uninstall()

    mock_cmd.assert_called_once()
    args = mock_cmd.call_args[0][0]
    assert args.package == "firefox"
    assert args.purge is True
    assert args.dry_run is True


@patch('linuxmole.interactive.cmd_uninstall_app')
@patch('linuxmole.interactive.input')
@patch('linuxmole.interactive.pause')
def test_simple_uninstall_list_orphans(mock_pause, mock_input, mock_cmd):
    """Test uninstall wizard - list orphans."""
    mock_input.return_value = "2"  # Option 2: list orphans

    simple_uninstall()

    mock_cmd.assert_called_once()
    args = mock_cmd.call_args[0][0]
    assert args.list_orphans is True


@patch('linuxmole.interactive.cmd_uninstall_app')
@patch('linuxmole.interactive.input')
@patch('linuxmole.interactive.prompt_bool')
def test_simple_uninstall_autoremove(mock_prompt, mock_input, mock_cmd):
    """Test uninstall wizard - autoremove."""
    mock_input.return_value = "3"  # Option 3: autoremove
    mock_prompt.return_value = True  # Confirm

    simple_uninstall()

    mock_cmd.assert_called_once()
    args = mock_cmd.call_args[0][0]
    assert args.autoremove is True


@patch('linuxmole.interactive.cmd_optimize')
@patch('linuxmole.interactive.prompt_bool')
@patch('linuxmole.interactive.is_root')
@patch('linuxmole.interactive.pause')
def test_simple_optimize(mock_pause, mock_root, mock_prompt, mock_cmd):
    """Test optimize wizard."""
    mock_root.return_value = True  # Running as root
    mock_prompt.side_effect = [True, True, False, False, True]
    # database=True, network=True, services=False, clear_cache=False, dry_run=True

    simple_optimize()

    mock_cmd.assert_called_once()
    args = mock_cmd.call_args[0][0]
    assert args.database is True
    assert args.network is True
    assert args.services is False
    assert args.clear_cache is False
    assert args.dry_run is True


# ══════════════════════════════════════════════════════════════
# Wizard Function Tests - Configuration
# ══════════════════════════════════════════════════════════════

@patch('linuxmole.interactive.cmd_whitelist')
@patch('linuxmole.interactive.input')
@patch('linuxmole.interactive.clear_screen')
@patch('linuxmole.interactive.print_header')
@patch('linuxmole.interactive.pause')
def test_simple_whitelist_show(mock_pause, mock_header, mock_clear, mock_input, mock_cmd):
    """Test whitelist wizard - show."""
    mock_input.side_effect = ["1", "0"]  # Option 1: show, then exit

    simple_whitelist()

    assert mock_cmd.call_count >= 1
    args = mock_cmd.call_args[0][0]
    assert args.add is None
    assert args.remove is None
    assert args.edit is False


@patch('linuxmole.interactive.cmd_whitelist')
@patch('linuxmole.interactive.input')
@patch('linuxmole.interactive.clear_screen')
@patch('linuxmole.interactive.print_header')
@patch('linuxmole.interactive.pause')
def test_simple_whitelist_add(mock_pause, mock_header, mock_clear, mock_input, mock_cmd):
    """Test whitelist wizard - add pattern."""
    mock_input.side_effect = ["2", "/test/*", "0"]
    # Option 2: add, pattern, then exit

    simple_whitelist()

    # Find the call with add argument
    add_call_found = False
    for call_args in mock_cmd.call_args_list:
        args = call_args[0][0]
        if args.add == "/test/*":
            add_call_found = True
            break
    assert add_call_found, "Add pattern call not found"


@patch('linuxmole.interactive.cmd_config')
@patch('linuxmole.interactive.input')
@patch('linuxmole.interactive.clear_screen')
@patch('linuxmole.interactive.print_header')
@patch('linuxmole.interactive.pause')
def test_simple_config_show(mock_pause, mock_header, mock_clear, mock_input, mock_cmd):
    """Test config wizard - show."""
    mock_input.return_value = "1"  # Option 1: show

    simple_config()

    mock_cmd.assert_called_once()
    args = mock_cmd.call_args[0][0]
    assert args.show is True
    assert args.edit is False
    assert args.reset is False


@patch('linuxmole.interactive.cmd_config')
@patch('linuxmole.interactive.input')
@patch('linuxmole.interactive.clear_screen')
@patch('linuxmole.interactive.print_header')
@patch('linuxmole.interactive.pause')
def test_simple_config_edit(mock_pause, mock_header, mock_clear, mock_input, mock_cmd):
    """Test config wizard - edit."""
    mock_input.return_value = "2"  # Option 2: edit

    simple_config()

    mock_cmd.assert_called_once()
    args = mock_cmd.call_args[0][0]
    assert args.edit is True


# ══════════════════════════════════════════════════════════════
# Wizard Function Tests - System
# ══════════════════════════════════════════════════════════════

@patch('linuxmole.interactive.run')
@patch('linuxmole.interactive.which')
@patch('linuxmole.interactive.prompt_bool')
@patch('linuxmole.interactive.pause')
def test_simple_update_success(mock_pause, mock_prompt, mock_which, mock_run):
    """Test update wizard - success."""
    mock_which.return_value = "/usr/bin/pipx"
    mock_prompt.return_value = True

    simple_update()

    mock_run.assert_called_once_with(["pipx", "upgrade", "linuxmole"])


@patch('linuxmole.interactive.which')
@patch('linuxmole.interactive.pause')
def test_simple_update_no_pipx(mock_pause, mock_which):
    """Test update wizard - pipx not found."""
    mock_which.return_value = None

    simple_update()

    # Should exit early, no run() call
    mock_pause.assert_called_once()


@patch('linuxmole.interactive.run')
@patch('linuxmole.interactive.which')
@patch('linuxmole.interactive.prompt_bool')
@patch('linuxmole.interactive.input')
@patch('sys.exit')
def test_simple_self_uninstall_confirmed(mock_exit, mock_input, mock_prompt, mock_which, mock_run):
    """Test self-uninstall - user confirms."""
    mock_which.return_value = "/usr/bin/pipx"
    mock_prompt.side_effect = [True, True]  # Two confirmations
    mock_input.return_value = ""  # Press Enter

    simple_self_uninstall()

    mock_run.assert_called_once_with(["pipx", "uninstall", "linuxmole"])
    mock_exit.assert_called_once_with(0)


@patch('linuxmole.interactive.prompt_bool')
@patch('linuxmole.interactive.pause')
def test_simple_self_uninstall_cancelled_first(mock_pause, mock_prompt):
    """Test self-uninstall - cancelled at first prompt."""
    mock_prompt.return_value = False  # First confirmation: No

    simple_self_uninstall()

    mock_pause.assert_called_once()


@patch('linuxmole.interactive.prompt_bool')
@patch('linuxmole.interactive.pause')
def test_simple_self_uninstall_cancelled_second(mock_pause, mock_prompt):
    """Test self-uninstall - cancelled at second prompt."""
    mock_prompt.side_effect = [True, False]  # First: Yes, Second: No

    simple_self_uninstall()

    mock_pause.assert_called_once()
