#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Helper utility functions for LinuxMole.
"""

from __future__ import annotations
import os
import sys
import shlex
import subprocess
from datetime import datetime
from typing import List, Optional

from linuxmole.logging_setup import logger
from linuxmole.output import p


def which(cmd: str) -> Optional[str]:
    """Find the full path of a command."""
    from shutil import which as _which
    return _which(cmd)


def run(cmd: List[str], dry_run: bool, check: bool = False) -> subprocess.CompletedProcess:
    """
    Execute a command with logging and dry-run support.

    Args:
        cmd: Command and arguments as list
        dry_run: If True, only print what would be executed
        check: If True, raise CalledProcessError on non-zero exit

    Returns:
        CompletedProcess instance
    """
    printable = " ".join(shlex.quote(x) for x in cmd)
    if dry_run:
        logger.debug(f"[DRY-RUN] Would execute: {printable}")
        p(f"[dry-run] {printable}")
        return subprocess.CompletedProcess(cmd, 0, stdout=b"", stderr=b"")
    logger.debug(f"Executing command: {printable}")
    p(f"[run] {printable}")
    result = subprocess.run(cmd, check=check)
    logger.debug(f"Command completed with return code: {result.returncode}")
    return result


def capture(cmd: List[str]) -> str:
    """
    Execute a command and capture its output.

    Args:
        cmd: Command and arguments as list

    Returns:
        Command output as string (stripped)
    """
    logger.debug(f"Capturing output: {' '.join(shlex.quote(x) for x in cmd)}")
    result = subprocess.check_output(cmd, text=True, stderr=subprocess.DEVNULL).strip()
    logger.debug(f"Captured {len(result)} bytes")
    return result


def is_root() -> bool:
    """Check if running as root."""
    return os.geteuid() == 0


def confirm(msg: str, assume_yes: bool) -> bool:
    """
    Ask user for confirmation.

    Args:
        msg: Confirmation message to display
        assume_yes: If True, automatically return True

    Returns:
        True if user confirmed (or assume_yes is True)
    """
    if assume_yes:
        return True
    ans = input(f"{msg} [y/N]: ").strip().lower()
    return ans in ("y", "yes")


def human_bytes(n: int) -> str:
    """
    Convert bytes to human-readable format.

    Args:
        n: Number of bytes

    Returns:
        Human-readable string (e.g., "1.5GB")
    """
    units = ["B", "KB", "MB", "GB", "TB", "PB"]
    f = float(n)
    for u in units:
        if f < 1024.0 or u == units[-1]:
            return f"{int(f)}B" if u == "B" else f"{f:.1f}{u}"
        f /= 1024.0
    return f"{n}B"


def format_size(n: Optional[int], unknown: bool = False) -> str:
    """
    Format size with optional unknown flag.

    Args:
        n: Number of bytes (or None)
        unknown: If True, append '+' to indicate approximate size

    Returns:
        Formatted size string
    """
    if n is None:
        return "size unavailable"
    s = human_bytes(n)
    return f"{s}+" if unknown else s


def bar(pct: float, width: int = 30) -> str:
    """
    Generate a simple ASCII progress bar.

    Args:
        pct: Percentage (0-100)
        width: Width of the bar in characters

    Returns:
        ASCII progress bar string
    """
    filled = int(width * pct / 100)
    return "[" + "#" * filled + "-" * (width - filled) + f"] {pct:.1f}%"


def now_str() -> str:
    """Return current timestamp as formatted string."""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def clear_screen() -> None:
    """Clear the terminal screen."""
    if sys.stdout.isatty():
        os.system("clear")


def pause(msg: str = "Press Enter to continue...") -> None:
    """Pause execution and wait for user input."""
    input(msg)


def maybe_reexec_with_sudo(reason: str) -> None:
    """
    Re-execute the current script with sudo if not running as root.

    Args:
        reason: Explanation of why root access is needed
    """
    if is_root():
        return
    p(f"[warn] {reason}")
    if not confirm("Re-execute with sudo?", assume_yes=False):
        p("[skip] Skipping operations that require root.")
        sys.exit(0)
    args = ["sudo", sys.executable] + sys.argv
    logger.debug(f"Re-executing with sudo: {args}")
    os.execvp("sudo", args)
