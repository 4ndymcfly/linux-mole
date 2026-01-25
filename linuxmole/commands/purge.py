#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Purge command implementation for LinuxMole.
"""

from __future__ import annotations
import argparse
import os
from pathlib import Path
from typing import List, Tuple

from linuxmole.output import section, p, line_ok, table, scan_status
from linuxmole.helpers import confirm, run, format_size
from linuxmole.config import ensure_config_files, purge_paths_file, load_purge_paths, load_whitelist, is_whitelisted
from linuxmole.system.paths import size_path_bytes


def cmd_purge(args: argparse.Namespace) -> None:
    """Purge build artifacts and cache directories from development projects."""
    section("Purge")
    ensure_config_files()
    if args.paths:
        p(f"Purge paths file: {purge_paths_file()}")
        return
    targets = load_purge_paths()
    patterns = ["node_modules", "target", "build", "dist", ".venv", "venv", "__pycache__"]
    whitelist = load_whitelist()
    candidates: List[Tuple[str, int, str]] = []
    with scan_status("Scanning projects..."):
        for base in targets:
            bpath = Path(base)
            if not bpath.exists():
                continue
            for p in bpath.rglob("*"):
                if not p.is_dir():
                    continue
                if p.name not in patterns:
                    continue
                pstr = str(p)
                if is_whitelisted(pstr, whitelist):
                    continue
                sz = size_path_bytes(p)
                if sz is None:
                    continue
                candidates.append((pstr, sz, p.name))
    candidates.sort(key=lambda x: x[1], reverse=True)
    if not candidates:
        line_ok("Nothing to purge")
        return
    rows = [[c[2], format_size(c[1]), c[0]] for c in candidates[:20]]
    table("Purge candidates (top 20)", ["Type", "Size", "Path"], rows)
    if not confirm(f"Purge {len(candidates)} items?", args.yes):
        p("Cancelled.")
        return
    for path, _, _ in candidates:
        run(["rm", "-rf", path], dry_run=False, check=False)
    p("Purge completed.")
