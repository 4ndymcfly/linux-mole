# -*- coding: utf-8 -*-
"""Tests for uninstall command."""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch
import sys

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import lm


class TestPackageDetection:
    """Tests for package detection functions."""

    def test_is_apt_package_found(self, mock_subprocess):
        """Test APT package detection when package exists."""
        mock_subprocess["check_output"].return_value = "ii  firefox   1.0  browser\n"

        result = lm.is_apt_package("firefox")

        assert result is True
        mock_subprocess["check_output"].assert_called_once()

    def test_is_apt_package_not_found(self, mock_subprocess):
        """Test APT package detection when package doesn't exist."""
        mock_subprocess["check_output"].side_effect = Exception("not found")

        result = lm.is_apt_package("nonexistent")

        assert result is False

    def test_is_snap_package_found(self, mock_subprocess, mocker):
        """Test Snap package detection when package exists."""
        mocker.patch("lm.which", return_value="/usr/bin/snap")
        mock_subprocess["check_output"].return_value = "firefox  1.0\nspotify  2.0\n"

        result = lm.is_snap_package("firefox")

        assert result is True

    def test_is_snap_package_not_available(self, mocker):
        """Test Snap package detection when snap is not available."""
        mocker.patch("lm.which", return_value=None)

        result = lm.is_snap_package("firefox")

        assert result is False

    def test_is_flatpak_package_found(self, mock_subprocess, mocker):
        """Test Flatpak package detection when package exists."""
        mocker.patch("lm.which", return_value="/usr/bin/flatpak")
        mock_subprocess["check_output"].return_value = "org.mozilla.firefox\norg.gimp.GIMP\n"

        result = lm.is_flatpak_package("org.mozilla.firefox")

        assert result is True

    def test_is_flatpak_package_not_available(self, mocker):
        """Test Flatpak package detection when flatpak is not available."""
        mocker.patch("lm.which", return_value=None)

        result = lm.is_flatpak_package("org.mozilla.firefox")

        assert result is False


class TestConfigPaths:
    """Tests for config path detection."""

    def test_get_package_config_paths(self, tmp_path, mocker):
        """Test getting config paths for a package."""
        # Mock home directory
        mocker.patch("lm.Path.home", return_value=tmp_path)

        # Create some config directories
        config_dir = tmp_path / ".config" / "testapp"
        config_dir.mkdir(parents=True)

        cache_dir = tmp_path / ".cache" / "testapp"
        cache_dir.mkdir(parents=True)

        # Get paths
        paths = lm.get_package_config_paths("testapp")

        # Should return existing paths only
        assert len(paths) == 2
        assert str(config_dir) in paths
        assert str(cache_dir) in paths

    def test_get_package_config_paths_empty(self, tmp_path, mocker):
        """Test getting config paths when none exist."""
        mocker.patch("lm.Path.home", return_value=tmp_path)

        paths = lm.get_package_config_paths("nonexistent")

        assert paths == []


class TestUninstallCommand:
    """Tests for cmd_uninstall_app function."""

    def test_uninstall_no_package(self, capsys, mocker):
        """Test uninstall without package name."""
        mocker.patch("lm.section")
        mocker.patch("lm.line_warn")

        args = Mock()
        args.package = None
        args.list_orphans = False
        args.autoremove = False
        args.broken = False

        lm.cmd_uninstall_app(args)

        lm.line_warn.assert_called()

    def test_uninstall_list_orphans(self, mock_subprocess, mocker):
        """Test listing orphaned packages."""
        mocker.patch("lm.section")
        mocker.patch("lm.which", return_value="/usr/bin/apt")
        mocker.patch("lm.table")
        mocker.patch("lm.p")
        mocker.patch("lm.line_ok")
        mock_subprocess["check_output"].return_value = "pkg1\npkg2\npkg3\n"

        args = Mock()
        args.list_orphans = True
        args.autoremove = False
        args.broken = False

        lm.cmd_uninstall_app(args)

        lm.table.assert_called_once()

    def test_uninstall_apt_package(self, mock_subprocess, mocker):
        """Test uninstalling an APT package."""
        mocker.patch("lm.section")
        mocker.patch("lm.p")
        mocker.patch("lm.is_apt_package", return_value=True)
        mocker.patch("lm.is_snap_package", return_value=False)
        mocker.patch("lm.is_flatpak_package", return_value=False)
        mocker.patch("lm.ensure_config_files")
        mocker.patch("lm.load_whitelist", return_value=[])
        mocker.patch("lm.is_whitelisted", return_value=False)
        mocker.patch("lm.show_plan")
        mocker.patch("lm.confirm", return_value=True)
        mocker.patch("lm.is_root", return_value=True)
        mocker.patch("lm.exec_actions")
        mocker.patch("lm.line_ok")
        mocker.patch("lm.get_package_config_paths", return_value=[])

        args = Mock()
        args.package = "vim"
        args.list_orphans = False
        args.autoremove = False
        args.broken = False
        args.purge = False
        args.dry_run = False
        args.yes = False

        lm.cmd_uninstall_app(args)

        lm.exec_actions.assert_called_once()
        lm.line_ok.assert_called()

    def test_uninstall_snap_package(self, mock_subprocess, mocker):
        """Test uninstalling a Snap package."""
        mocker.patch("lm.section")
        mocker.patch("lm.p")
        mocker.patch("lm.is_apt_package", return_value=False)
        mocker.patch("lm.is_snap_package", return_value=True)
        mocker.patch("lm.is_flatpak_package", return_value=False)
        mocker.patch("lm.ensure_config_files")
        mocker.patch("lm.load_whitelist", return_value=[])
        mocker.patch("lm.is_whitelisted", return_value=False)
        mocker.patch("lm.show_plan")
        mocker.patch("lm.confirm", return_value=True)
        mocker.patch("lm.is_root", return_value=True)
        mocker.patch("lm.exec_actions")
        mocker.patch("lm.line_ok")
        mocker.patch("lm.Path.exists", return_value=False)

        args = Mock()
        args.package = "spotify"
        args.list_orphans = False
        args.autoremove = False
        args.broken = False
        args.purge = False
        args.dry_run = False
        args.yes = False

        lm.cmd_uninstall_app(args)

        lm.exec_actions.assert_called_once()

    def test_uninstall_package_not_found(self, mocker):
        """Test uninstalling a package that doesn't exist."""
        mocker.patch("lm.section")
        mocker.patch("lm.p")
        mocker.patch("lm.line_warn")
        mocker.patch("lm.is_apt_package", return_value=False)
        mocker.patch("lm.is_snap_package", return_value=False)
        mocker.patch("lm.is_flatpak_package", return_value=False)

        args = Mock()
        args.package = "nonexistent"
        args.list_orphans = False
        args.autoremove = False
        args.broken = False

        lm.cmd_uninstall_app(args)

        lm.line_warn.assert_called()

    def test_uninstall_whitelisted_package(self, mocker):
        """Test uninstalling a whitelisted package."""
        mocker.patch("lm.section")
        mocker.patch("lm.p")
        mocker.patch("lm.line_warn")
        mocker.patch("lm.is_apt_package", return_value=True)
        mocker.patch("lm.ensure_config_files")
        mocker.patch("lm.load_whitelist", return_value=["/uninstall/vim"])
        mocker.patch("lm.is_whitelisted", return_value=True)
        mocker.patch("lm.get_package_config_paths", return_value=[])

        args = Mock()
        args.package = "vim"
        args.list_orphans = False
        args.autoremove = False
        args.broken = False
        args.purge = False

        lm.cmd_uninstall_app(args)

        lm.line_warn.assert_called()

    def test_uninstall_cancelled(self, mocker):
        """Test uninstalling when user cancels."""
        mocker.patch("lm.section")
        mocker.patch("lm.p")
        mocker.patch("lm.is_apt_package", return_value=True)
        mocker.patch("lm.is_snap_package", return_value=False)
        mocker.patch("lm.is_flatpak_package", return_value=False)
        mocker.patch("lm.ensure_config_files")
        mocker.patch("lm.load_whitelist", return_value=[])
        mocker.patch("lm.is_whitelisted", return_value=False)
        mocker.patch("lm.show_plan")
        mocker.patch("lm.confirm", return_value=False)
        mocker.patch("lm.get_package_config_paths", return_value=[])

        args = Mock()
        args.package = "vim"
        args.list_orphans = False
        args.autoremove = False
        args.broken = False
        args.purge = False
        args.dry_run = False
        args.yes = False

        lm.cmd_uninstall_app(args)

        lm.p.assert_any_call("Cancelled.")
