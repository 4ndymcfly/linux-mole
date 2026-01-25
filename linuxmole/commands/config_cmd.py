#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Config command implementation for LinuxMole.
"""

from __future__ import annotations
import argparse
import os

try:
    import tomllib
except ImportError:
    try:
        import tomli as tomllib
    except ImportError:
        tomllib = None

from linuxmole.constants import RICH
from linuxmole.logging_setup import logger
from linuxmole.output import section, p, line_ok, line_warn
from linuxmole.helpers import confirm, run
from linuxmole.config import config_file_path, default_config, load_config, save_config


def cmd_config(args: argparse.Namespace) -> None:
    """Manage configuration file."""
    section("Configuration Management")

    config_path = config_file_path()

    # Handle --reset flag
    if hasattr(args, 'reset') and args.reset:
        if not confirm("Reset configuration to defaults?", False):
            p("Cancelled.")
            return

        config = default_config()
        if save_config(config):
            line_ok(f"Configuration reset to defaults: {config_path}")
        else:
            line_warn("Failed to reset configuration")
        return

    # Handle --edit flag
    if hasattr(args, 'edit') and args.edit:
        # Ensure config exists
        if not config_path.exists():
            p("Config file doesn't exist yet. Creating with defaults...")
            save_config(default_config())

        editor = os.environ.get("EDITOR")
        if not editor:
            line_warn("$EDITOR environment variable not set")
            p("\nSet your editor with:")
            p("  export EDITOR=nano    # or vim, code, etc.")
            return

        logger.info(f"Opening config in editor: {editor}")
        run([editor, str(config_path)], dry_run=False, check=False)
        return

    # Default: show configuration
    p(f"Configuration file: {config_path}")
    p("")

    if not config_path.exists():
        line_warn("Config file doesn't exist yet")
        p("")
        p("The config file will be created automatically when needed,")
        p("or you can create it now with:")
        p("  lm config --reset")
        p("")
        p("Default configuration:")
        config = default_config()
    else:
        if tomllib is None:
            line_warn("TOML library not available")
            p("Install tomli to read configuration:")
            p("  pip install tomli")
            return

        config = load_config()

    # Display configuration
    p("")
    for section_name, section_values in config.items():
        p(f"[bold cyan][{section_name}][/bold cyan]" if RICH else f"[{section_name}]")
        for key, value in section_values.items():
            if isinstance(value, list):
                p(f"  {key} = [")
                for item in value:
                    p(f"    {repr(item)},")
                p("  ]")
            else:
                p(f"  {key} = {repr(value)}")
        p("")

    p("Commands:")
    p("  lm config             Show current configuration")
    p("  lm config --edit      Edit configuration in $EDITOR")
    p("  lm config --reset     Reset to default configuration")
