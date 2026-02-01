#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Analyze command implementation with ncdu-style TUI for LinuxMole.
"""

from __future__ import annotations
import argparse
import os
import sys
import subprocess
from pathlib import Path
from typing import List, Tuple, Optional

from linuxmole.constants import TEXTUAL, TEXTUAL_ERROR
from linuxmole.logging_setup import logger
from linuxmole.output import section, p, line_ok, line_warn, table, scan_status
from linuxmole.helpers import which, capture, confirm, format_size, bar
from linuxmole.system.paths import du_bytes
from linuxmole.config import load_config, is_whitelisted

# Import Textual classes only if available
if TEXTUAL:
    from textual.app import App, ComposeResult
    from textual.binding import Binding
    from textual.containers import Vertical, Container
    from textual.widgets import Header, Footer, Static, DataTable
    from textual.reactive import reactive
    from textual.coordinate import Coordinate


if TEXTUAL:
    class DiskUsageHeader(Static):
        """Header widget displaying current path and statistics."""

        current_path = reactive("")
        total_size = reactive(0)
        total_items = reactive(0)

        def render(self) -> str:
            """Render the header with path and statistics."""
            size_str = format_size(self.total_size)

            # Truncate path if too long
            display_path = self.current_path or "/"
            max_path_len = 60
            if len(display_path) > max_path_len:
                display_path = "..." + display_path[-(max_path_len-3):]

            return f"""[bold white]ncdu-style Disk Usage[/bold white] - {display_path}

[dim]Total disk usage:[/dim] [bold cyan]{size_str}[/bold cyan]    [dim]Items:[/dim] [bold yellow]{self.total_items}[/bold yellow]"""


    class NcduApp(App):
        """ncdu-style TUI for disk usage analysis."""

        CSS = """
        DiskUsageHeader {
            dock: top;
            height: 5;
            border: solid $primary;
            padding: 1;
            background: $panel;
        }

        DataTable {
            height: 100%;
        }

        #help_footer {
            dock: bottom;
            height: 3;
            background: $panel;
            border: solid $accent;
            padding: 0 1;
        }
        """

        BINDINGS = [
            Binding("q", "quit", "Quit", key_display="Q"),
            Binding("r", "refresh", "Refresh", key_display="R"),
            Binding("enter", "enter_directory", "Enter", show=False),
            Binding("backspace", "parent_directory", "Parent", show=False),
            Binding("escape", "parent_directory", "Parent", show=False),
            Binding("d", "delete_item", "Delete", key_display="D"),
            Binding("up", "cursor_up", "Up", show=False),
            Binding("down", "cursor_down", "Down", show=False),
            Binding("right", "enter_directory", "Right", show=False),
            Binding("left", "parent_directory", "Left", show=False),
        ]

        TITLE = "LinuxMole - Disk Usage Analyzer (ncdu-style)"

        def __init__(self, start_path: str = "/"):
            super().__init__()
            self.start_path = os.path.abspath(start_path)
            self.current_path = self.start_path
            self.history: List[str] = []  # Navigation history

        def compose(self) -> ComposeResult:
            """Compose the UI layout."""
            yield Header()
            yield DiskUsageHeader(id="header")
            yield DataTable(id="items_table", cursor_type="row")
            yield Static(
                "[bold white]→[/bold white]/[bold white]Enter[/bold white]: Open  "
                "[bold white]←[/bold white]/[bold white]Backspace[/bold white]: Parent  "
                "[bold white]D[/bold white]: Delete  "
                "[bold white]R[/bold white]: Refresh  "
                "[bold white]Q[/bold white]: Quit",
                id="help_footer"
            )
            yield Footer()

        def on_mount(self) -> None:
            """Initialize the table and load data."""
            # Log terminal info for debugging
            import os as os_module
            term = os_module.environ.get('TERM', 'unknown')
            term_program = os_module.environ.get('TERM_PROGRAM', 'unknown')
            logger.debug(f"Terminal: TERM={term}, TERM_PROGRAM={term_program}")

            table = self.query_one("#items_table", DataTable)
            table.cursor_type = "row"
            table.zebra_stripes = True

            # Add columns
            table.add_columns("Size", "Usage", "Name")

            # Load initial data
            self.load_directory(self.current_path)
            table.focus()

        def load_directory(self, path: str) -> None:
            """Load directory contents into the table."""
            table = self.query_one("#items_table", DataTable)
            header = self.query_one("#header", DiskUsageHeader)

            # Clear existing rows
            table.clear()

            # Update header
            header.current_path = path
            self.current_path = path

            try:
                # Get directory entries with sizes
                items = self._scan_directory(path)

                if not items:
                    header.total_size = 0
                    header.total_items = 0
                    table.add_row("--", "", "[dim](empty directory)[/dim]")
                    return

                # Calculate total and find max for bar sizing
                total_size = sum(size for _, size, _ in items)
                max_size = max((size for _, size, _ in items), default=1)

                # Update header
                header.total_size = total_size
                header.total_items = len(items)

                # Add parent directory option if not at root
                if path != "/":
                    table.add_row(
                        "[dim]/..       [/dim]",
                        "",
                        "[bold cyan]/..[/bold cyan] [dim](parent directory)[/dim]"
                    )

                # Add rows to table
                for item_path, size, is_dir in items:
                    size_str = format_size(size)

                    # Calculate bar (proportional to max in this directory)
                    bar_width = int((size / max_size * 20)) if max_size > 0 else 0
                    bar_visual = "█" * bar_width

                    # Color based on type
                    if is_dir:
                        name_display = f"[bold cyan]/{os.path.basename(item_path)}[/bold cyan]"
                    else:
                        name_display = os.path.basename(item_path)

                    table.add_row(
                        f"[yellow]{size_str:>12}[/yellow]",
                        f"[green]{bar_visual}[/green]",
                        name_display,
                        key=item_path  # Store full path as key
                    )

            except PermissionError:
                header.total_size = 0
                header.total_items = 0
                table.add_row("--", "", "[red]Permission denied[/red]")
            except Exception as e:
                logger.error(f"Error loading directory {path}: {e}")
                header.total_size = 0
                header.total_items = 0
                table.add_row("--", "", f"[red]Error: {e}[/red]")

        def _scan_directory(self, path: str) -> List[Tuple[str, int, bool]]:
            """
            Scan directory and return list of (path, size, is_dir) tuples.
            Returns sorted by size descending.
            """
            items: List[Tuple[str, int, bool]] = []

            try:
                with os.scandir(path) as entries:
                    for entry in entries:
                        try:
                            full_path = entry.path
                            is_dir = entry.is_dir(follow_symlinks=False)

                            if is_dir:
                                # Get directory size
                                size = du_bytes(full_path) or 0
                            else:
                                # Get file size
                                size = entry.stat(follow_symlinks=False).st_size

                            items.append((full_path, size, is_dir))
                        except (PermissionError, OSError):
                            # Skip items we can't access
                            continue

                # Sort by size descending
                items.sort(key=lambda x: x[1], reverse=True)

            except PermissionError:
                raise
            except Exception as e:
                logger.error(f"Error scanning {path}: {e}")
                raise

            return items

        def on_data_table_row_selected(self, event) -> None:
            """Handle row selection (double-click or enter on some terminals)."""
            self.action_enter_directory()

        def action_enter_directory(self) -> None:
            """Enter the selected directory or open file."""
            table = self.query_one("#items_table", DataTable)

            if table.row_count == 0:
                return

            # Get selected row
            row_key = table.cursor_row
            if row_key is None or row_key < 0:
                return

            try:
                # Get row data
                row = table.get_row_at(row_key)
                if not row:
                    return

                # Extract name from third column
                name_cell = str(row[2])

                # Check if parent directory
                if "/.." in name_cell or "(parent" in name_cell:
                    self.action_parent_directory()
                    return

                # Try to get path from row metadata first
                try:
                    # Get all rows to find the one with matching index
                    row_index = 0
                    for r in table.rows:
                        if row_index == row_key:
                            if hasattr(r, 'key') and r.key:
                                full_path = r.key
                                break
                        row_index += 1
                    else:
                        # Fallback: extract from name
                        raise AttributeError("No key found")
                except (AttributeError, IndexError):
                    # Fallback: extract from name
                    # Remove ANSI codes and formatting
                    clean_name = name_cell.replace("[bold cyan]", "").replace("[/bold cyan]", "")
                    clean_name = clean_name.replace("[dim]", "").replace("[/dim]", "")
                    clean_name = clean_name.split("(")[0].strip()  # Remove (parent directory) etc
                    clean_name = clean_name.lstrip("/")  # Remove leading /
                    full_path = os.path.join(self.current_path, clean_name)

                # Check if directory
                if os.path.isdir(full_path):
                    # Save current path to history
                    self.history.append(self.current_path)
                    # Load new directory
                    self.load_directory(full_path)
                else:
                    # For files, show message
                    self.notify(f"Cannot enter file: {os.path.basename(full_path)}")

            except Exception as e:
                logger.error(f"Error entering directory: {e}")
                self.notify(f"Error: {e}", severity="error")

        def action_parent_directory(self) -> None:
            """Go to parent directory."""
            if self.current_path == "/":
                self.notify("Already at root directory")
                return

            # Use history if available
            if self.history:
                parent_path = self.history.pop()
            else:
                parent_path = os.path.dirname(self.current_path)

            self.load_directory(parent_path)

        def action_delete_item(self) -> None:
            """Delete the selected item (with confirmation and whitelist check)."""
            table = self.query_one("#items_table", DataTable)

            if table.row_count == 0:
                return

            row_key = table.cursor_row
            if row_key is None or row_key < 0:
                return

            try:
                row = table.get_row_at(row_key)
                if not row:
                    return

                # Get path from row key or construct it
                name_cell = str(row[2])

                # Skip parent directory
                if "/.." in name_cell or "(parent" in name_cell:
                    self.notify("Cannot delete parent directory marker")
                    return

                # Get full path
                if hasattr(table.get_row(row_key), 'key'):
                    full_path = table.get_row(row_key).key
                else:
                    clean_name = name_cell.replace("[bold cyan]", "").replace("[/bold cyan]", "")
                    clean_name = clean_name.split("[")[0].strip().lstrip("/")
                    full_path = os.path.join(self.current_path, clean_name)

                # Check whitelist
                if is_whitelisted(full_path):
                    self.notify(f"⚠️  Protected by whitelist: {os.path.basename(full_path)}", severity="warning")
                    return

                # Show confirmation (simplified for TUI)
                self.notify(f"Delete function not yet implemented in TUI. Use CLI: lm purge", severity="information")

            except Exception as e:
                logger.error(f"Error in delete action: {e}")
                self.notify(f"Error: {e}", severity="error")

        def action_refresh(self) -> None:
            """Refresh the current directory view."""
            self.load_directory(self.current_path)
            self.notify("Directory refreshed")


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

    # Validate path exists
    if not os.path.exists(target):
        line_warn(f"Path does not exist: {target}")
        return

    # Launch TUI if requested
    if hasattr(args, 'tui') and args.tui:
        if not TEXTUAL:
            # Show detailed error
            p("")
            line_warn("Textual library is not available.")

            if TEXTUAL_ERROR:
                p(f"Error: {TEXTUAL_ERROR}")
                logger.debug(f"Textual import error: {TEXTUAL_ERROR}")

            p("")
            p("The TUI interface requires the 'textual' library.")
            p("This should have been installed automatically with linuxmole.")
            p("")

            # Offer to install
            auto_install = tui_config.get("auto_install", True)
            if confirm("Would you like to try installing/upgrading textual?", auto_install):
                p("Installing textual...")
                try:
                    result = subprocess.run(
                        [sys.executable, "-m", "pip", "install", "--upgrade", "textual>=0.47.0"],
                        capture_output=True,
                        text=True,
                        timeout=120
                    )

                    if result.returncode == 0:
                        line_ok("Textual installed/upgraded successfully!")
                        p("")
                        p("⚠️  IMPORTANT: Please restart your terminal session or run:")
                        p("    source ~/.bashrc  (or ~/.zshrc)")
                        p("")
                        p("Then try again: lm analyze --tui")
                        return
                    else:
                        line_warn("Failed to install textual.")
                        if result.stderr:
                            logger.error(f"pip error: {result.stderr}")
                        p("Falling back to table view...")
                except subprocess.TimeoutExpired:
                    line_warn("Installation timed out.")
                    p("Falling back to table view...")
                except Exception as e:
                    line_warn(f"Error installing textual: {e}")
                    logger.error(f"Installation exception: {e}")
                    p("Falling back to table view...")
            else:
                p("Falling back to table view...")
        else:
            # Launch ncdu-style TUI
            try:
                app = NcduApp(start_path=target)
                app.run()
                return
            except Exception as e:
                line_warn(f"TUI failed to start: {e}")
                logger.error(f"TUI exception: {e}", exc_info=True)
                p("")
                p("Falling back to table view...")

    # Fallback: Table view
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
