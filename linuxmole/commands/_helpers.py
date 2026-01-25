#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Internal helper functions for command modules.
"""

from __future__ import annotations
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from linuxmole.constants import RICH, console
from linuxmole.output import table, p
from linuxmole.helpers import format_size
from linuxmole.system.metrics import disk_usage_bytes

if RICH:
    from rich.text import Text


def add_summary(
    items: List[Dict],
    label: str,
    count: int,
    size_bytes: Optional[int],
    size_note: Optional[str] = None,
    count_display: Optional[str] = None,
    size_unknown: bool = False,
    risk: str = "low",
) -> None:
    """Add an item to the summary list."""
    items.append({
        "label": label,
        "count": count,
        "count_display": count_display,
        "bytes": size_bytes,
        "note": size_note,
        "unknown": size_unknown,
        "risk": risk,
    })


def render_summary(items: List[Dict]) -> None:
    """Render summary table of cleanup items."""
    rows = []
    for it in items:
        count = it["count_display"] if it["count_display"] is not None else str(it["count"])
        size_str = format_size(it["bytes"], it.get("unknown", False))
        if it["note"]:
            size_str = f"{size_str} ({it['note']})"
        if RICH and console is not None:
            rows.append([it["label"], count, Text(size_str, style="green")])
        else:
            rows.append([it["label"], count, size_str])
    table("Summary", ["Item", "Count", "Estimated space"], rows)


def render_risks(items: List[Dict]) -> None:
    """Render risk level table."""
    rows = []
    for it in items:
        risk = it.get("risk", "low")
        label = it["label"]
        if RICH and console is not None:
            style = {"low": "green", "med": "yellow", "high": "red"}.get(risk, "white")
            rows.append([label, Text(risk.upper(), style=style)])
        else:
            rows.append([label, risk.upper()])
    table("Risk levels", ["Item", "Risk"], rows)


def summary_totals(items: List[Dict]) -> Tuple[int, bool, int, int]:
    """Calculate total bytes, unknown flag, total items, and categories."""
    total_bytes = 0
    unknown = False
    total_items = 0
    categories = len(items)
    for it in items:
        count = it["count"]
        if count > 0:
            total_items += count
        if it.get("unknown"):
            unknown = True
        if it["bytes"] is None:
            if count > 0:
                unknown = True
        else:
            total_bytes += it["bytes"]
    return total_bytes, unknown, total_items, categories


def write_detail_list(lines: List[str], filename: str = "clean-list.txt") -> Optional[Path]:
    """Write detailed file list to config directory."""
    if not lines:
        return None
    cfg = Path("~/.config/linuxmole").expanduser()
    cfg.mkdir(parents=True, exist_ok=True)
    path = cfg / filename
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def print_final_summary(
    dry_run: bool,
    total_bytes: int,
    unknown: bool,
    items: int,
    categories: int,
    log_path: Optional[Path],
) -> None:
    """Print final summary after cleanup operation."""
    p("\n" + "=" * 70)
    if dry_run:
        p("Dry run complete - no changes made")
    else:
        p("Operation completed")
    potential = format_size(total_bytes, unknown)
    if RICH and console is not None:
        line = Text("Potential space: ")
        line.append(potential, style="green")
        line.append(f" | Items: {items} | Categories: {categories}")
        console.print(line)
    else:
        p(f"Potential space: {potential} | Items: {items} | Categories: {categories}")
    disk_b = disk_usage_bytes("/")
    if disk_b:
        _, _, avail = disk_b
        if RICH and console is not None:
            line = Text("Free space now: ")
            line.append(format_size(avail), style="green")
            console.print(line)
        else:
            p(f"Free space now: {format_size(avail)}")
    if log_path:
        p(f"Detailed file list: {log_path}")
    if dry_run:
        p("Run without --dry-run to apply these changes")
    p("=" * 70)
