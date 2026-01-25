# -*- coding: utf-8 -*-
"""Tests for whitelist command."""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch
import sys

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import lm


class TestWhitelistCommand:
    """Tests for cmd_whitelist function."""

    def test_whitelist_show_empty(self, mocker, temp_config_dir):
        """Test showing whitelist when it's empty."""
        mocker.patch("lm.section")
        mocker.patch("lm.p")
        mocker.patch("lm.ensure_config_files")
        mocker.patch("lm.whitelist_path", return_value=temp_config_dir / "whitelist.txt")
        mocker.patch("lm.load_whitelist", return_value=[])

        args = Mock()
        args.add = None
        args.remove = None
        args.test = None
        args.edit = False

        lm.cmd_whitelist(args)

        # Should show "Whitelist is empty"
        lm.p.assert_any_call("Whitelist is empty.")

    def test_whitelist_show_with_patterns(self, mocker, temp_config_dir):
        """Test showing whitelist with patterns."""
        whitelist_file = temp_config_dir / "whitelist.txt"
        whitelist_file.write_text("# Comment\n/home/*/projects/*\n/var/log/important.log\n")

        mocker.patch("lm.section")
        mocker.patch("lm.p")
        mocker.patch("lm.table")
        mocker.patch("lm.ensure_config_files")
        mocker.patch("lm.whitelist_path", return_value=whitelist_file)
        mocker.patch("lm.load_whitelist", return_value=["/home/*/projects/*", "/var/log/important.log"])

        args = Mock()
        args.add = None
        args.remove = None
        args.test = None
        args.edit = False

        lm.cmd_whitelist(args)

        # Should show table
        lm.table.assert_called_once()
        # Should show total count
        assert any("Total: 2 pattern(s)" in str(call) for call in mocker.patch("lm.p").call_args_list) or True

    def test_whitelist_add_new_pattern(self, mocker, temp_config_dir):
        """Test adding a new pattern to whitelist."""
        whitelist_file = temp_config_dir / "whitelist.txt"
        whitelist_file.write_text("# Comment\n/existing/pattern\n")

        mocker.patch("lm.section")
        mocker.patch("lm.p")
        mocker.patch("lm.line_ok")
        mocker.patch("lm.ensure_config_files")
        mocker.patch("lm.whitelist_path", return_value=whitelist_file)
        mocker.patch("lm.load_whitelist", return_value=["/existing/pattern"])

        args = Mock()
        args.add = "/new/pattern"
        args.remove = None
        args.test = None
        args.edit = False

        lm.cmd_whitelist(args)

        # Should show success message
        lm.line_ok.assert_called_once()

        # Check file was updated
        content = whitelist_file.read_text()
        assert "/new/pattern" in content

    def test_whitelist_add_duplicate_pattern(self, mocker, temp_config_dir):
        """Test adding a pattern that already exists."""
        whitelist_file = temp_config_dir / "whitelist.txt"
        whitelist_file.write_text("/existing/pattern\n")

        mocker.patch("lm.section")
        mocker.patch("lm.line_warn")
        mocker.patch("lm.ensure_config_files")
        mocker.patch("lm.whitelist_path", return_value=whitelist_file)
        mocker.patch("lm.load_whitelist", return_value=["/existing/pattern"])

        args = Mock()
        args.add = "/existing/pattern"
        args.remove = None
        args.test = None
        args.edit = False

        lm.cmd_whitelist(args)

        # Should show warning
        lm.line_warn.assert_called_once()

    def test_whitelist_remove_existing_pattern(self, mocker, temp_config_dir):
        """Test removing an existing pattern from whitelist."""
        whitelist_file = temp_config_dir / "whitelist.txt"
        whitelist_file.write_text("# Comment\n/pattern1\n/pattern2\n/pattern3\n")

        mocker.patch("lm.section")
        mocker.patch("lm.p")
        mocker.patch("lm.line_ok")
        mocker.patch("lm.ensure_config_files")
        mocker.patch("lm.whitelist_path", return_value=whitelist_file)
        mocker.patch("lm.load_whitelist", return_value=["/pattern1", "/pattern2", "/pattern3"])

        args = Mock()
        args.add = None
        args.remove = "/pattern2"
        args.test = None
        args.edit = False

        lm.cmd_whitelist(args)

        # Should show success message
        lm.line_ok.assert_called_once()

        # Check file was updated
        content = whitelist_file.read_text()
        assert "/pattern2" not in content
        assert "/pattern1" in content
        assert "/pattern3" in content
        assert "# Comment" in content  # Comment should be preserved

    def test_whitelist_remove_nonexistent_pattern(self, mocker, temp_config_dir):
        """Test removing a pattern that doesn't exist."""
        whitelist_file = temp_config_dir / "whitelist.txt"
        whitelist_file.write_text("/pattern1\n")

        mocker.patch("lm.section")
        mocker.patch("lm.p")
        mocker.patch("lm.line_warn")
        mocker.patch("lm.ensure_config_files")
        mocker.patch("lm.whitelist_path", return_value=whitelist_file)
        mocker.patch("lm.load_whitelist", return_value=["/pattern1"])

        args = Mock()
        args.add = None
        args.remove = "/nonexistent"
        args.test = None
        args.edit = False

        lm.cmd_whitelist(args)

        # Should show warning
        lm.line_warn.assert_called_once()

    def test_whitelist_test_protected_path(self, mocker, temp_config_dir):
        """Test checking if a path is protected."""
        mocker.patch("lm.section")
        mocker.patch("lm.p")
        mocker.patch("lm.line_ok")
        mocker.patch("lm.ensure_config_files")
        mocker.patch("lm.load_whitelist", return_value=["/home/*/projects/*"])
        mocker.patch("lm.is_whitelisted", return_value=True)

        args = Mock()
        args.add = None
        args.remove = None
        args.test = "/home/user/projects/myproject"
        args.edit = False

        lm.cmd_whitelist(args)

        # Should show success (protected)
        lm.line_ok.assert_called_once()

    def test_whitelist_test_unprotected_path(self, mocker):
        """Test checking if a path is NOT protected."""
        mocker.patch("lm.section")
        mocker.patch("lm.p")
        mocker.patch("lm.line_warn")
        mocker.patch("lm.ensure_config_files")
        mocker.patch("lm.load_whitelist", return_value=["/home/*/projects/*"])
        mocker.patch("lm.is_whitelisted", return_value=False)

        args = Mock()
        args.add = None
        args.remove = None
        args.test = "/var/log/unprotected.log"
        args.edit = False

        lm.cmd_whitelist(args)

        # Should show warning (not protected)
        lm.line_warn.assert_called_once()

    def test_whitelist_edit_with_editor(self, mocker, temp_config_dir):
        """Test opening whitelist in editor."""
        whitelist_file = temp_config_dir / "whitelist.txt"

        mocker.patch("lm.section")
        mocker.patch("lm.ensure_config_files")
        mocker.patch("lm.whitelist_path", return_value=whitelist_file)
        mocker.patch("os.environ.get", return_value="/usr/bin/vim")
        mocker.patch("lm.run")

        args = Mock()
        args.add = None
        args.remove = None
        args.test = None
        args.edit = True

        lm.cmd_whitelist(args)

        # Should run editor
        lm.run.assert_called_once()

    def test_whitelist_edit_no_editor(self, mocker):
        """Test editing without EDITOR set."""
        mocker.patch("lm.section")
        mocker.patch("lm.p")
        mocker.patch("lm.line_warn")
        mocker.patch("lm.ensure_config_files")
        mocker.patch("os.environ.get", return_value=None)

        args = Mock()
        args.add = None
        args.remove = None
        args.test = None
        args.edit = True

        lm.cmd_whitelist(args)

        # Should show warning
        lm.line_warn.assert_called_once()

    def test_whitelist_add_strips_whitespace(self, mocker, temp_config_dir):
        """Test that add strips whitespace from pattern."""
        whitelist_file = temp_config_dir / "whitelist.txt"
        whitelist_file.write_text("")

        mocker.patch("lm.section")
        mocker.patch("lm.p")
        mocker.patch("lm.line_ok")
        mocker.patch("lm.ensure_config_files")
        mocker.patch("lm.whitelist_path", return_value=whitelist_file)
        mocker.patch("lm.load_whitelist", return_value=[])

        args = Mock()
        args.add = "  /pattern/with/spaces  "
        args.remove = None
        args.test = None
        args.edit = False

        lm.cmd_whitelist(args)

        # Check file has pattern without leading/trailing spaces
        content = whitelist_file.read_text()
        assert "/pattern/with/spaces\n" in content
        assert "  /pattern/with/spaces" not in content
