# -*- coding: utf-8 -*-
"""Tests for output functions."""

import pytest
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import lm


class TestPrintFunctions:
    """Tests for print helper functions."""

    def test_p_function(self, capsys):
        """Test p() function."""
        lm.p("Test message")
        captured = capsys.readouterr()
        assert "Test message" in captured.out

    def test_p_empty(self, capsys):
        """Test p() with empty string."""
        lm.p()
        captured = capsys.readouterr()
        assert captured.out == "\n"


class TestVersionAndBanner:
    """Tests for version and banner."""

    def test_version_constant(self):
        """Test VERSION constant exists and has correct format."""
        assert hasattr(lm, "VERSION")
        # Verify version follows semver format (X.Y.Z)
        import re
        assert re.match(r'^\d+\.\d+\.\d+$', lm.VERSION), f"VERSION should be semver format, got: {lm.VERSION}"

    def test_banner_constant(self):
        """Test BANNER constant exists."""
        assert hasattr(lm, "BANNER")
        assert len(lm.BANNER) > 0
        # Banner is ASCII art, just check it exists and has content

    def test_project_url(self):
        """Test PROJECT_URL constant."""
        assert hasattr(lm, "PROJECT_URL")
        assert "github.com" in lm.PROJECT_URL.lower()


class TestConfigPaths:
    """Tests for config path functions."""

    def test_config_dir(self):
        """Test config_dir() function."""
        config_path = lm.config_dir()
        assert config_path is not None
        assert "linuxmole" in str(config_path).lower()

    def test_whitelist_path(self):
        """Test whitelist_path() function."""
        whitelist = lm.whitelist_path()
        assert whitelist is not None
        assert "whitelist.txt" in str(whitelist)


class TestWhitelistFunctions:
    """Tests for whitelist functions."""

    def test_load_whitelist_empty(self, temp_config_dir, mocker):
        """Test loading empty whitelist."""
        mocker.patch("lm.config_dir", return_value=temp_config_dir)
        whitelist = lm.load_whitelist()
        assert isinstance(whitelist, list)
        # May be empty or have default entries

    def test_load_whitelist_with_patterns(self, temp_config_dir, mocker):
        """Test loading whitelist with patterns."""
        mocker.patch("lm.config_dir", return_value=temp_config_dir)
        whitelist_file = temp_config_dir / "whitelist.txt"
        whitelist_file.write_text("*.log\n*.txt\n")

        whitelist = lm.load_whitelist()
        assert "*.log" in whitelist
        assert "*.txt" in whitelist

    def test_is_whitelisted_match(self):
        """Test is_whitelisted() with matching pattern."""
        patterns = ["*.log", "*.txt"]
        assert lm.is_whitelisted("/var/log/test.log", patterns) is True
        assert lm.is_whitelisted("/home/user/doc.txt", patterns) is True

    def test_is_whitelisted_no_match(self):
        """Test is_whitelisted() with non-matching pattern."""
        patterns = ["*.log", "*.txt"]
        assert lm.is_whitelisted("/var/log/test.py", patterns) is False
        assert lm.is_whitelisted("/home/user/doc.sh", patterns) is False

    def test_is_whitelisted_empty_patterns(self):
        """Test is_whitelisted() with empty patterns."""
        assert lm.is_whitelisted("/any/path", []) is False
