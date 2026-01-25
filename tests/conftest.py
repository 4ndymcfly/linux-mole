# -*- coding: utf-8 -*-
"""Shared fixtures for LinuxMole tests."""

import pytest
import sys
import os
from pathlib import Path
from unittest.mock import Mock, MagicMock

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import lm


@pytest.fixture
def mock_console():
    """Mock rich console."""
    if lm.RICH:
        original_console = lm.console
        lm.console = Mock()
        yield lm.console
        lm.console = original_console
    else:
        yield None


@pytest.fixture
def temp_config_dir(tmp_path):
    """Create temporary config directory."""
    config_dir = tmp_path / ".config" / "linuxmole"
    config_dir.mkdir(parents=True, exist_ok=True)
    return config_dir


@pytest.fixture
def mock_subprocess(mocker):
    """Mock subprocess calls."""
    mock_run = mocker.patch("subprocess.run")
    mock_run.return_value = Mock(returncode=0, stdout=b"", stderr=b"")

    mock_check_output = mocker.patch("subprocess.check_output")
    mock_check_output.return_value = b"mock output"

    return {"run": mock_run, "check_output": mock_check_output}


@pytest.fixture
def mock_root_user(mocker):
    """Mock root user check."""
    mocker.patch("os.geteuid", return_value=0)


@pytest.fixture
def mock_non_root_user(mocker):
    """Mock non-root user check."""
    mocker.patch("os.geteuid", return_value=1000)


@pytest.fixture
def capture_output(capsys):
    """Capture stdout/stderr."""
    return capsys
