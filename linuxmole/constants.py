#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Constants and global variables for LinuxMole.
"""

from __future__ import annotations
import re

# Version and branding
BANNER = r""" _      _                     __  __       _
| |    (_)                   |  \/  |     | |
| |     _ _ __  _   ___  __  | \  / | ___ | | ___
| |    | | '_ \| | | \ \/ /  | |\/| |/ _ \| |/ _ \
| |____| | | | | |_| |>  <   | |  | | (_) | |  __/
|______|_|_| |_|\__,_/_/\_\  |_|  |_|\___/|_|\___|"""
PROJECT_URL = "https://github.com/4ndymcfly/linux-mole"
TAGLINE = "Safe maintenance for Linux + Docker."
VERSION = "1.0.3"

# Regular expressions
_SIZE_RE = re.compile(r"^\s*([0-9]+(?:\.[0-9]+)?)\s*([KMGTP]?i?B)?\s*$", re.IGNORECASE)

# Rich (optional) output
RICH = False
try:
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich.text import Text
    from rich import box
    RICH = True
    console = Console(highlight=False)
except Exception:
    console = None

# Textual TUI support (optional)
TEXTUAL = False
try:
    from textual.app import App, ComposeResult
    from textual.containers import Container, Horizontal, Vertical
    from textual.widgets import Header, Footer, DirectoryTree, Static, Label
    from textual.binding import Binding
    from textual.reactive import reactive
    TEXTUAL = True
except Exception:
    TEXTUAL = False
