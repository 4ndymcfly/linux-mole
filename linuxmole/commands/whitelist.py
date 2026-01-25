#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Whitelist management command for LinuxMole.
"""

from __future__ import annotations
import argparse
import os
import fnmatch

from linuxmole.logging_setup import logger
from linuxmole.output import section, p, line_ok, line_warn, table
from linuxmole.helpers import run
from linuxmole.config import (
    ensure_config_files,
    whitelist_path,
    load_whitelist,
    is_whitelisted,
)


def cmd_whitelist(args: argparse.Namespace) -> None:
    """Manage whitelist of protected paths."""
    section("Whitelist Management")

    ensure_config_files()
    path = whitelist_path()

    # Handle --add flag
    if args.add:
        patterns = load_whitelist()
        pattern = args.add.strip()

        # Check if pattern already exists
        if pattern in patterns:
            line_warn(f"Pattern already in whitelist: {pattern}")
            return

        # Add pattern to file
        with open(path, 'a', encoding='utf-8') as f:
            f.write(f"{pattern}\n")

        logger.info(f"Added pattern to whitelist: {pattern}")
        line_ok(f"Added to whitelist: {pattern}")
        p("")
        p(f"Total patterns: {len(patterns) + 1}")
        return

    # Handle --remove flag
    if args.remove:
        patterns = load_whitelist()
        pattern = args.remove.strip()

        # Check if pattern exists
        if pattern not in patterns:
            line_warn(f"Pattern not found in whitelist: {pattern}")
            p("\nCurrent patterns:")
            for p_existing in patterns:
                p(f"  - {p_existing}")
            return

        # Remove pattern from list
        patterns.remove(pattern)

        # Read original file to preserve comments
        original_lines = path.read_text(encoding='utf-8').splitlines()
        new_lines = []

        for line in original_lines:
            stripped = line.strip()
            # Keep comments and empty lines
            if not stripped or stripped.startswith("#"):
                new_lines.append(line)
            # Keep patterns that are not the one to remove
            elif os.path.expanduser(stripped) != pattern:
                new_lines.append(line)

        # Write back
        path.write_text("\n".join(new_lines) + "\n", encoding='utf-8')

        logger.info(f"Removed pattern from whitelist: {pattern}")
        line_ok(f"Removed from whitelist: {pattern}")
        p("")
        p(f"Total patterns: {len(patterns)}")
        return

    # Handle --test flag
    if args.test:
        patterns = load_whitelist()
        test_path = args.test.strip()

        if is_whitelisted(test_path, patterns):
            line_ok(f"✓ Protected (whitelisted): {test_path}")
            p("")
            p("Matching pattern(s):")
            for pat in patterns:
                if fnmatch.fnmatch(test_path, pat):
                    p(f"  - {pat}")
        else:
            line_warn(f"✗ NOT protected: {test_path}")
            p("")
            p("Tip: Add pattern with:")
            p(f"  lm whitelist --add '{test_path}'")
        return

    # Handle --edit flag
    if args.edit:
        editor = os.environ.get("EDITOR")
        if not editor:
            line_warn("$EDITOR environment variable not set")
            p("\nSet your editor with:")
            p("  export EDITOR=nano    # or vim, code, etc.")
            return

        logger.info(f"Opening whitelist in editor: {editor}")
        run([editor, str(path)], dry_run=False, check=False)
        return

    # Default: show whitelist with table
    patterns = load_whitelist()

    # Read all lines to get comments too
    all_lines = path.read_text(encoding='utf-8').splitlines() if path.exists() else []

    if not patterns:
        p("Whitelist is empty.")
        p("")
        p("Add patterns to protect paths from cleanup:")
        p("  lm whitelist --add '/home/*/projects/*'")
        p("  lm whitelist --add '/var/log/important.log'")
        p("")
        p("Other commands:")
        p("  lm whitelist --test /path/to/file")
        p("  lm whitelist --edit")
        return

    # Show table with patterns
    p(f"Whitelist file: {path}")
    p("")

    rows = []
    for i, pattern in enumerate(patterns, 1):
        rows.append([str(i), pattern])

    table("Protected Patterns", ["#", "Pattern"], rows)

    p("")
    p(f"Total: {len(patterns)} pattern(s)")
    p("")
    p("Commands:")
    p("  lm whitelist --add PATTERN      Add new pattern")
    p("  lm whitelist --remove PATTERN   Remove pattern")
    p("  lm whitelist --test PATH        Test if path is protected")
    p("  lm whitelist --edit             Edit in $EDITOR")
