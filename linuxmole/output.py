#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Output formatting functions for LinuxMole.
"""

from __future__ import annotations
import sys
import threading
import time
from typing import List, Tuple, Optional
from contextlib import contextmanager

from linuxmole.constants import RICH, TEXTUAL, console, BANNER, PROJECT_URL, TAGLINE

# Conditional imports for rich
if RICH:
    from rich.panel import Panel
    from rich.text import Text
    from rich.table import Table
    from rich import box


def p(text: str = "") -> None:
    """Print text with optional rich formatting."""
    if RICH:
        console.print(text, highlight=False)
    else:
        print(text)


def title(s: str) -> None:
    """Print a title with formatting."""
    if RICH:
        console.print(Panel(Text(s, style="bold"), expand=False))
    else:
        print(f"\n=== {s} ===")


def print_banner(banner_style: Optional[str] = None, url_style: Optional[str] = None) -> None:
    """Print the LinuxMole banner."""
    if RICH and console is not None and banner_style:
        console.print(BANNER, style=banner_style, highlight=False)
    else:
        p(BANNER)
    p("")
    if RICH and console is not None and url_style:
        console.print(PROJECT_URL, style=url_style, highlight=False)
    else:
        p(f"{PROJECT_URL}")
    p("")
    p(f"{TAGLINE}")
    p("")


def print_header() -> None:
    """Print the LinuxMole header."""
    if RICH and console is not None:
        console.print("LinuxMole", style="bold green", highlight=False)
    else:
        print("LinuxMole")


def section(s: str) -> None:
    """Print a section header."""
    if RICH and console is not None:
        console.print(f"\n\n[bold cyan]➤ {s}[/bold cyan]")
        console.rule("", style="bold cyan")
    else:
        p(f"\n\n➤ {s}")


def line_ok(s: str) -> None:
    """Print a success line."""
    if RICH and console is not None:
        console.print(f"[bold green]✓[/bold green] {s}", highlight=False)
    else:
        p(f"✓ {s}")


def line_do(s: str) -> None:
    """Print an action line."""
    if RICH and console is not None:
        console.print(f"[cyan]→[/cyan] {s}", highlight=False)
    else:
        p(f"→ {s}")


def line_skip(s: str) -> None:
    """Print a skip line."""
    if RICH and console is not None:
        console.print(f"[dim]○ {s}[/dim]", highlight=False)
    else:
        p(f"○ {s}")


def line_warn(s: str) -> None:
    """Print a warning line."""
    if RICH and console is not None:
        console.print(f"[bold yellow]! {s}[/bold yellow]", highlight=False)
    else:
        p(f"! {s}")


def kv_table(title_str: str, rows: List[Tuple[str, str]]) -> None:
    """Print a key-value table."""
    if RICH:
        t = Table(title=title_str, box=box.SIMPLE_HEAVY, show_header=False, title_style="bold")
        t.add_column("Key", style="bold")
        t.add_column("Value")
        for k, v in rows:
            t.add_row(k, v)
        console.print(t)
    else:
        print(f"\n-- {title_str} --")
        for k, v in rows:
            print(f"{k}: {v}")


def table(title_str: str, headers: List[str], rows: List[List[str]]) -> None:
    """Print a formatted table."""
    if RICH:
        t = Table(title=title_str, box=box.SIMPLE_HEAVY, header_style="bold", title_style="bold")
        for h in headers:
            t.add_column(h, overflow="fold")
        for r in rows:
            t.add_row(*r)
        console.print(t)
    else:
        print(f"\n-- {title_str} --")
        print(" | ".join(headers))
        print("-" * 80)
        for r in rows:
            print(" | ".join(r))


@contextmanager
def scan_status(msg: str):
    """Context manager for showing status with spinner."""
    if RICH and console is not None:
        with console.status(msg, spinner="dots"):
            yield
        return
    stop = threading.Event()
    spinner = ["|", "/", "-", "\\"]

    def _spin() -> None:
        i = 0
        while not stop.is_set():
            sys.stdout.write(f"\r{spinner[i % len(spinner)]} {msg}")
            sys.stdout.flush()
            i += 1
            time.sleep(0.1)

    t = threading.Thread(target=_spin, daemon=True)
    t.start()
    try:
        yield
    finally:
        stop.set()
        t.join()
        sys.stdout.write("\r")
        sys.stdout.flush()
        line_ok(msg)
