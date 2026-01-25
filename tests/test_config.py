# -*- coding: utf-8 -*-
"""Tests for config management functionality."""

import pytest
from pathlib import Path
from unittest.mock import Mock, mock_open, patch
import sys

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import lm


class TestConfigPaths:
    """Tests for config file path functions."""

    def test_config_file_path(self, mocker):
        """Test config file path is correct."""
        mocker.patch("lm.config_dir", return_value=Path("/home/user/.config/linuxmole"))

        path = lm.config_file_path()

        assert path == Path("/home/user/.config/linuxmole/config.toml")
        assert str(path).endswith("config.toml")


class TestDefaultConfig:
    """Tests for default configuration."""

    def test_default_config_structure(self):
        """Test default config has expected structure."""
        config = lm.default_config()

        # Check main sections exist
        assert "whitelist" in config
        assert "clean" in config
        assert "paths" in config
        assert "optimize" in config
        assert "tui" in config

    def test_default_config_whitelist(self):
        """Test default whitelist configuration."""
        config = lm.default_config()

        assert config["whitelist"]["auto_protect_system"] is True
        assert isinstance(config["whitelist"]["patterns"], list)
        assert len(config["whitelist"]["patterns"]) > 0
        # Check some critical patterns
        assert any("/etc/passwd" in p for p in config["whitelist"]["patterns"])
        assert any("/.ssh/" in p for p in config["whitelist"]["patterns"])

    def test_default_config_clean(self):
        """Test default clean configuration."""
        config = lm.default_config()

        assert config["clean"]["auto_confirm"] is False
        assert config["clean"]["preserve_recent_days"] == 7
        assert "default_journal_time" in config["clean"]
        assert "default_journal_size" in config["clean"]

    def test_default_config_paths(self):
        """Test default paths configuration."""
        config = lm.default_config()

        assert isinstance(config["paths"]["purge_paths"], list)
        assert "." in config["paths"]["analyze_default"]

    def test_default_config_optimize(self):
        """Test default optimize configuration."""
        config = lm.default_config()

        assert config["optimize"]["auto_database"] is True
        assert config["optimize"]["auto_network"] is True
        assert config["optimize"]["auto_services"] is True
        assert config["optimize"]["auto_clear_cache"] is False

    def test_default_config_tui(self):
        """Test default TUI configuration."""
        config = lm.default_config()

        assert config["tui"]["auto_install"] is True


class TestLoadConfig:
    """Tests for loading configuration."""

    def test_load_config_file_not_exists(self, temp_config_dir, mocker):
        """Test load_config returns defaults when file doesn't exist."""
        config_path = temp_config_dir / "config.toml"
        mocker.patch("lm.config_file_path", return_value=config_path)

        config = lm.load_config()

        # Should return defaults
        assert "whitelist" in config
        assert "clean" in config

    def test_load_config_tomllib_not_available(self, temp_config_dir, mocker):
        """Test load_config returns defaults when tomllib not available."""
        config_path = temp_config_dir / "config.toml"
        config_path.write_text("[test]\nkey = 'value'\n", encoding="utf-8")

        mocker.patch("lm.config_file_path", return_value=config_path)
        mocker.patch("lm.tomllib", None)

        config = lm.load_config()

        # Should return defaults and log warning
        assert "whitelist" in config

    @pytest.mark.skipif(lm.tomllib is None, reason="tomllib not available")
    def test_load_config_valid_file(self, temp_config_dir, mocker):
        """Test load_config reads valid TOML file."""
        config_path = temp_config_dir / "config.toml"

        # Write a simple valid config
        config_content = """
[whitelist]
auto_protect_system = false

[clean]
auto_confirm = true
preserve_recent_days = 14
"""
        config_path.write_text(config_content, encoding="utf-8")

        mocker.patch("lm.config_file_path", return_value=config_path)

        config = lm.load_config()

        # Should load from file
        assert config["whitelist"]["auto_protect_system"] is False
        assert config["clean"]["auto_confirm"] is True
        assert config["clean"]["preserve_recent_days"] == 14

    def test_load_config_invalid_file(self, temp_config_dir, mocker):
        """Test load_config returns defaults when file is invalid."""
        config_path = temp_config_dir / "config.toml"
        config_path.write_text("invalid toml {{{", encoding="utf-8")

        mocker.patch("lm.config_file_path", return_value=config_path)

        config = lm.load_config()

        # Should return defaults on error
        assert "whitelist" in config


class TestSaveConfig:
    """Tests for saving configuration."""

    def test_save_config_creates_directory(self, temp_config_dir, mocker):
        """Test save_config creates config directory if needed."""
        config_path = temp_config_dir / "subdir" / "config.toml"
        mocker.patch("lm.config_file_path", return_value=config_path)

        config = {"test": {"key": "value"}}
        result = lm.save_config(config)

        assert result is True
        assert config_path.parent.exists()

    def test_save_config_writes_file(self, temp_config_dir, mocker):
        """Test save_config writes config to file."""
        config_path = temp_config_dir / "config.toml"
        mocker.patch("lm.config_file_path", return_value=config_path)

        config = {
            "section1": {
                "bool_val": True,
                "int_val": 42,
                "str_val": "test",
                "list_val": ["a", "b", "c"]
            }
        }

        result = lm.save_config(config)

        assert result is True
        assert config_path.exists()

        content = config_path.read_text(encoding="utf-8")
        assert "[section1]" in content
        assert "bool_val = true" in content
        assert "int_val = 42" in content
        assert 'str_val = "test"' in content
        assert '"a", "b", "c"' in content

    def test_save_config_handles_error(self, mocker):
        """Test save_config handles errors gracefully."""
        # Mock config_file_path to return path in non-writable location
        mocker.patch("lm.config_file_path", return_value=Path("/root/config.toml"))

        config = {"test": {"key": "value"}}
        result = lm.save_config(config)

        # Should return False on error
        assert result is False


class TestConfigCommand:
    """Tests for config command."""

    def test_config_show_file_not_exists(self, temp_config_dir, mocker):
        """Test config command when file doesn't exist."""
        config_path = temp_config_dir / "config.toml"
        mocker.patch("lm.config_file_path", return_value=config_path)
        mocker.patch("lm.section")
        mocker.patch("lm.line_warn")
        mocker.patch("lm.p")

        args = Mock()
        args.reset = False
        args.edit = False

        lm.cmd_config(args)

        # Should show warning
        lm.line_warn.assert_called()
        assert any("doesn't exist" in str(call) for call in lm.line_warn.call_args_list)

    def test_config_reset(self, temp_config_dir, mocker):
        """Test config --reset."""
        config_path = temp_config_dir / "config.toml"
        mocker.patch("lm.config_file_path", return_value=config_path)
        mocker.patch("lm.section")
        mocker.patch("lm.confirm", return_value=True)
        mocker.patch("lm.line_ok")
        mocker.patch("lm.p")

        args = Mock()
        args.reset = True
        args.edit = False

        lm.cmd_config(args)

        # Should save default config
        assert config_path.exists()
        content = config_path.read_text()
        assert "[whitelist]" in content

    def test_config_reset_cancelled(self, temp_config_dir, mocker):
        """Test config --reset when user cancels."""
        config_path = temp_config_dir / "config.toml"
        mocker.patch("lm.config_file_path", return_value=config_path)
        mocker.patch("lm.section")
        mocker.patch("lm.confirm", return_value=False)
        mocker.patch("lm.p")

        args = Mock()
        args.reset = True
        args.edit = False

        lm.cmd_config(args)

        # Should not create file
        assert not config_path.exists()

    def test_config_edit_no_editor(self, temp_config_dir, mocker):
        """Test config --edit without $EDITOR set."""
        config_path = temp_config_dir / "config.toml"
        mocker.patch("lm.config_file_path", return_value=config_path)
        mocker.patch("lm.section")
        mocker.patch("lm.line_warn")
        mocker.patch("lm.p")
        mocker.patch.dict("os.environ", {}, clear=True)

        args = Mock()
        args.reset = False
        args.edit = True

        lm.cmd_config(args)

        # Should show warning
        lm.line_warn.assert_called()
        assert any("EDITOR" in str(call) for call in lm.line_warn.call_args_list)

    def test_config_edit_with_editor(self, temp_config_dir, mocker):
        """Test config --edit with $EDITOR set."""
        config_path = temp_config_dir / "config.toml"
        mocker.patch("lm.config_file_path", return_value=config_path)
        mocker.patch("lm.section")
        mocker.patch("lm.run")
        mocker.patch.dict("os.environ", {"EDITOR": "nano"})

        # Config file doesn't exist, should be created
        mock_save = mocker.patch("lm.save_config")
        mocker.patch("lm.default_config", return_value={})

        args = Mock()
        args.reset = False
        args.edit = True

        lm.cmd_config(args)

        # Should create default config first
        mock_save.assert_called_once()
        # Should run editor
        lm.run.assert_called_once()

    def test_config_show_with_valid_config(self, temp_config_dir, mocker):
        """Test config command shows configuration."""
        config_path = temp_config_dir / "config.toml"
        config_path.write_text("[test]\nkey = 'value'\n", encoding="utf-8")

        mocker.patch("lm.config_file_path", return_value=config_path)
        mocker.patch("lm.section")
        mocker.patch("lm.p")

        # Mock load_config to return simple config
        mocker.patch("lm.load_config", return_value={"test": {"key": "value"}})

        args = Mock()
        args.reset = False
        args.edit = False

        lm.cmd_config(args)

        # Should display config
        lm.p.assert_called()
        # Check that section name was printed
        calls_str = " ".join(str(call) for call in lm.p.call_args_list)
        assert "test" in calls_str.lower()
