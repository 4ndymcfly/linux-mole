#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Configuration management for LinuxMole.
"""

from __future__ import annotations
import fnmatch
import os
from pathlib import Path
from typing import Dict, List, Any

from linuxmole.logging_setup import logger

# TOML support (tomllib for Python 3.11+, tomli for <3.11)
try:
    import tomllib
except ModuleNotFoundError:
    try:
        import tomli as tomllib  # type: ignore
    except ModuleNotFoundError:
        tomllib = None  # type: ignore


def config_dir() -> Path:
    """Get the configuration directory path."""
    return Path("~/.config/linuxmole").expanduser()


def whitelist_path() -> Path:
    """Get the whitelist file path."""
    return config_dir() / "whitelist.txt"


def purge_paths_file() -> Path:
    """Get the purge paths file path."""
    return config_dir() / "purge_paths"


def config_file_path() -> Path:
    """Get the config file path."""
    return config_dir() / "config.toml"


def default_config() -> Dict[str, Any]:
    """Return default configuration."""
    return {
        "whitelist": {
            "auto_protect_system": True,
            "patterns": [
                "/home/*/.ssh/*",
                "/home/*/.gnupg/*",
                "/etc/passwd",
                "/etc/shadow",
                "/etc/fstab",
                "/boot/*",
                "/sys/*",
                "/proc/*"
            ]
        },
        "clean": {
            "auto_confirm": False,
            "preserve_recent_days": 7,
            "default_journal_time": "3d",
            "default_journal_size": "500M"
        },
        "paths": {
            "purge_paths": [
                "~/Projects",
                "~/GitHub",
                "~/dev",
                "~/work"
            ],
            "analyze_default": "."
        },
        "optimize": {
            "auto_database": True,
            "auto_network": True,
            "auto_services": True,
            "auto_clear_cache": False
        },
        "tui": {
            "auto_install": True
        }
    }


def load_config() -> Dict[str, Any]:
    """Load configuration from config.toml or return defaults."""
    config_path = config_file_path()

    if not config_path.exists():
        logger.debug("Config file not found, using defaults")
        return default_config()

    # Check tomllib availability
    if tomllib is None:
        logger.warning("TOML library not available, using defaults")
        return default_config()

    try:
        with open(config_path, "rb") as f:
            config = tomllib.load(f)
        logger.debug(f"Loaded config from {config_path}")
        return config
    except Exception as e:
        logger.error(f"Error loading config: {e}")
        return default_config()


def save_config(config: Dict[str, Any]) -> bool:
    """Save configuration to config.toml."""
    config_path = config_file_path()

    try:
        # Ensure config directory exists
        config_path.parent.mkdir(parents=True, exist_ok=True)

        # Convert dict to TOML string manually (simple implementation)
        lines = []
        for section, values in config.items():
            lines.append(f"[{section}]")
            for key, value in values.items():
                if isinstance(value, bool):
                    lines.append(f"{key} = {str(value).lower()}")
                elif isinstance(value, (int, float)):
                    lines.append(f"{key} = {value}")
                elif isinstance(value, str):
                    lines.append(f'{key} = "{value}"')
                elif isinstance(value, list):
                    # Format list
                    formatted_items = []
                    for item in value:
                        if isinstance(item, str):
                            formatted_items.append(f'"{item}"')
                        else:
                            formatted_items.append(str(item))
                    lines.append(f"{key} = [{', '.join(formatted_items)}]")
            lines.append("")  # Empty line between sections

        config_path.write_text("\n".join(lines), encoding="utf-8")
        logger.info(f"Saved config to {config_path}")
        return True
    except Exception as e:
        logger.error(f"Error saving config: {e}")
        return False


def load_whitelist() -> List[str]:
    """Load whitelist patterns from file."""
    path = whitelist_path()
    if not path.exists():
        return []
    patterns = []
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        patterns.append(os.path.expanduser(line))
    return patterns


def is_whitelisted(path: str, patterns: List[str]) -> bool:
    """Check if a path matches any whitelist pattern."""
    for pat in patterns:
        if fnmatch.fnmatch(path, pat):
            return True
    return False


def ensure_config_files() -> None:
    """Ensure configuration files exist."""
    cfg = config_dir()
    cfg.mkdir(parents=True, exist_ok=True)
    if not whitelist_path().exists():
        whitelist_path().write_text("# Add glob patterns to protect paths\n", encoding="utf-8")
    if not purge_paths_file().exists():
        purge_paths_file().write_text("# One path per line\n", encoding="utf-8")


def load_purge_paths() -> List[str]:
    """Load purge paths from config file."""
    ensure_config_files()
    path = purge_paths_file()
    res = []
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        res.append(os.path.expanduser(line))
    if not res:
        res = [str(Path("~/Projects").expanduser()),
               str(Path("~/GitHub").expanduser()),
               str(Path("~/dev").expanduser()),
               str(Path("~/work").expanduser())]
    return res
