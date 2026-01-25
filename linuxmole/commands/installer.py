#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Installer files cleanup command for LinuxMole.
"""

from __future__ import annotations
import argparse
import os

from linuxmole.output import section, p, line_ok, table, scan_status
from linuxmole.helpers import confirm, run, format_size
from linuxmole.config import ensure_config_files, load_whitelist, is_whitelisted
from linuxmole.system.paths import list_installer_files


def cmd_installer(args: argparse.Namespace) -> None:
    """Clean up installer files (.deb, .rpm, .AppImage, etc.)."""
    section("Installer")
    ensure_config_files()
    whitelist = load_whitelist()
    with scan_status("Scanning installer files..."):
        files = list_installer_files()
    files = [(p, sz) for (p, sz) in files if not is_whitelisted(p, whitelist)]
    if not files:
        line_ok("No installer files found")
        return
    rows = [[os.path.basename(p), format_size(sz), p] for p, sz in files[:20]]
    table("Installer files (top 20)", ["Name", "Size", "Path"], rows)
    if not confirm(f"Remove {len(files)} files?", args.yes):
        p("Cancelled.")
        return
    for p, _ in files:
        run(["rm", "-f", p], dry_run=False, check=False)
    p("Installer cleanup completed.")
