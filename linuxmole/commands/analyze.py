#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Analyze command implementation and TUI for LinuxMole.
"""

from __future__ import annotations
import argparse
import os
import sys
import subprocess
from pathlib import Path

from linuxmole.constants import TEXTUAL
from linuxmole.logging_setup import logger
from linuxmole.output import section, p, line_ok, line_warn, table, scan_status
from linuxmole.helpers import which, capture, confirm, format_size, bar
from linuxmole.system.paths import du_bytes
from linuxmole.config import load_config

# Import Textual classes only if available
if TEXTUAL:
    from textual.app import App, ComposeResult
    from textual.binding import Binding
    from textual.containers import Horizontal, Vertical
    from textual.widgets import Header, Footer, DirectoryTree, Static
    from textual.reactive import reactive


if TEXTUAL:
    class DiskUsageInfo(Static):
        """Widget to display information about selected directory."""

        path = reactive("")
        size = reactive(0)
        total_size = reactive(1)

        def render(self) -> str:
            """Render the disk usage information."""
            if not self.path:
                return "[dim]Select a directory to see details[/dim]"

            percentage = (self.size / self.total_size * 100) if self.total_size > 0 else 0
            size_str = format_size(self.size)

            return f"""[bold cyan]Path:[/bold cyan] {self.path}
[bold yellow]Size:[/bold yellow] {size_str}
[bold green]Percentage:[/bold green] {percentage:.1f}% of total"""

    class DiskAnalyzerApp(App):
        """Interactive TUI for disk usage analysis."""

        CSS = """
        Screen {
            layers: base overlay notes notifications;
        }

        DiskUsageInfo {
            dock: top;
            height: 5;
            border: solid $primary;
            padding: 1;
        }

        DirectoryTree {
            scrollbar-gutter: stable;
            dock: left;
            width: 60%;
            height: 100%;
        }

        #info_panel {
            dock: right;
            width: 40%;
            height: 100%;
            border: solid $accent;
            padding: 1;
        }

        Container {
            height: 100%;
        }
        """

        BINDINGS = [
            Binding("q", "quit", "Quit", key_display="Q"),
            Binding("r", "refresh", "Refresh", key_display="R"),
            ("d", "toggle_dark", "Toggle Dark Mode"),
        ]

        TITLE = "LinuxMole - Disk Usage Analyzer"
        SUB_TITLE = "Navigate with arrows, press Q to quit"

        def __init__(self, start_path: str = "/"):
            super().__init__()
            self.start_path = start_path
            self.total_size = 0

        def compose(self) -> ComposeResult:
            """Compose the UI layout."""
            yield Header()
            with Horizontal():
                yield DirectoryTree(self.start_path, id="tree")
                with Vertical(id="info_panel"):
                    yield DiskUsageInfo(id="disk_info")
                    yield Static(
                        "[dim]Use arrow keys to navigate\nPress Enter to expand\nPress Q to quit[/dim]",
                        id="help_text"
                    )
            yield Footer()

        def on_mount(self) -> None:
            """Handle mount event."""
            self.query_one(DirectoryTree).focus()
            # Calculate total size of start path
            self.total_size = du_bytes(self.start_path) or 1

        def on_directory_tree_directory_selected(
            self, event: DirectoryTree.DirectorySelected
        ) -> None:
            """Handle directory selection."""
            path = str(event.path)
            size = du_bytes(path) or 0

            disk_info = self.query_one("#disk_info", DiskUsageInfo)
            disk_info.path = path
            disk_info.size = size
            disk_info.total_size = self.total_size

        def on_directory_tree_file_selected(
            self, event: DirectoryTree.FileSelected
        ) -> None:
            """Handle file selection."""
            path = str(event.path)
            try:
                size = Path(path).stat().st_size
            except Exception:
                size = 0

            disk_info = self.query_one("#disk_info", DiskUsageInfo)
            disk_info.path = path
            disk_info.size = size
            disk_info.total_size = self.total_size

        def action_refresh(self) -> None:
            """Refresh the directory tree."""
            tree = self.query_one(DirectoryTree)
            tree.reload()
            self.total_size = du_bytes(self.start_path) or 1
            self.notify("Directory tree refreshed")


def cmd_analyze(args: argparse.Namespace) -> None:
    """Analyze disk usage of a directory."""
    # Load config and apply defaults
    config = load_config()
    paths_config = config.get("paths", {})
    tui_config = config.get("tui", {})

    # Use default path from config if path is "."
    if args.path == ".":
        args.path = paths_config.get("analyze_default", ".")

    target = os.path.expanduser(args.path)

    # Launch TUI if requested
    if hasattr(args, 'tui') and args.tui:
        if not TEXTUAL:
            # Offer to install textual
            p("")
            line_warn("Textual library is not installed.")
            p("Textual is required for the interactive TUI interface.")
            p("")

            # Use auto_install from config
            auto_install = tui_config.get("auto_install", True)
            if confirm("Would you like to install textual and its dependencies?", auto_install):
                p("Installing textual...")
                try:
                    # Try to install textual
                    result = subprocess.run(
                        [sys.executable, "-m", "pip", "install", "textual>=0.47.0"],
                        capture_output=True,
                        text=True,
                        timeout=60
                    )

                    if result.returncode == 0:
                        line_ok("Textual installed successfully!")
                        p("Please run the command again to use the TUI.")
                        p("Note: You may need to restart your terminal session.")
                        return
                    else:
                        line_warn("Failed to install textual.")
                        logger.debug(f"pip install error: {result.stderr}")
                        p("Falling back to table view...")
                except subprocess.TimeoutExpired:
                    line_warn("Installation timed out.")
                    p("Falling back to table view...")
                except Exception as e:
                    line_warn(f"Error installing textual: {e}")
                    logger.debug(f"Installation exception: {e}")
                    p("Falling back to table view...")
            else:
                p("Falling back to table view...")
        else:
            app = DiskAnalyzerApp(start_path=target)
            app.run()
            return

    section("Analyze")
    with scan_status(f"Scanning {target}..."):
        if which("du"):
            try:
                out = capture(["du", "-b", "--max-depth=1", target])
            except Exception:
                out = ""
        else:
            out = ""
    if not out:
        line_warn("Unable to analyze path")
        return
    items = []
    for line in out.splitlines():
        parts = line.split("\t", 1)
        if len(parts) != 2:
            continue
        size = int(parts[0])
        path = parts[1]
        if os.path.abspath(path) == os.path.abspath(target):
            continue
        items.append((path, size))
    items.sort(key=lambda x: x[1], reverse=True)
    total = sum(sz for _, sz in items) or 1
    rows = []
    for path, size in items[:args.top]:
        pct = (size / total) * 100.0
        rows.append([f"{pct:5.1f}%", bar(pct, 16), os.path.basename(path), format_size(size)])
    table("Top entries", ["%", "Bar", "Name", "Size"], rows)
