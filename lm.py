#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
lm.py - Mole-like maintenance CLI for Ubuntu + Docker

Features:
- Structured output (rich panels/tables) if 'rich' is installed; fallback to plain text.
- Safe-by-default: shows plan, supports --dry-run, --yes.
- Docker maintenance: unused containers/images/networks/volumes, builder cache, system usage, log stats + optional truncation.
- System maintenance: journald vacuum, tmpfiles clean, apt clean/autoremove.
"""

from __future__ import annotations

import argparse
import fnmatch
import json
import logging
import os
import shlex
import re
import subprocess
import sys
import threading
import time
from contextlib import contextmanager
from functools import cmp_to_key
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any

# TOML support (tomllib for Python 3.11+, tomli for <3.11)
try:
    import tomllib
except ModuleNotFoundError:
    try:
        import tomli as tomllib  # type: ignore
    except ModuleNotFoundError:
        tomllib = None  # type: ignore

# -----------------------------
# Rich (optional) output
# -----------------------------
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

BANNER = r""" _      _                     __  __       _
| |    (_)                   |  \/  |     | |
| |     _ _ __  _   ___  __  | \  / | ___ | | ___
| |    | | '_ \| | | \ \/ /  | |\/| |/ _ \| |/ _ \
| |____| | | | | |_| |>  <   | |  | | (_) | |  __/
|______|_|_| |_|\__,_/_/\_\  |_|  |_|\___/|_|\___|"""
PROJECT_URL = "https://github.com/4ndymcfly/linux-mole"
TAGLINE = "Safe maintenance for Linux + Docker."
VERSION = "1.0.0"


def p(text: str = "") -> None:
    if RICH:
        console.print(text, highlight=False)
    else:
        print(text)

def title(s: str) -> None:
    if RICH:
        console.print(Panel(Text(s, style="bold"), expand=False))
    else:
        print(f"\n=== {s} ===")

def print_banner(banner_style: Optional[str] = None, url_style: Optional[str] = None) -> None:
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
    if RICH and console is not None:
        console.print("LinuxMole", style="bold green", highlight=False)
    else:
        print("LinuxMole")

def section(s: str) -> None:
    if RICH and console is not None:
        console.print(f"\n\n[bold cyan]➤ {s}[/bold cyan]")
        console.rule("", style="bold cyan")
    else:
        p(f"\n\n➤ {s}")

def line_ok(s: str) -> None:
    if RICH and console is not None:
        console.print(f"[bold green]✓[/bold green] {s}", highlight=False)
    else:
        p(f"✓ {s}")

def line_do(s: str) -> None:
    if RICH and console is not None:
        console.print(f"[cyan]→[/cyan] {s}", highlight=False)
    else:
        p(f"→ {s}")

def line_skip(s: str) -> None:
    if RICH and console is not None:
        console.print(f"[dim]○ {s}[/dim]", highlight=False)
    else:
        p(f"○ {s}")

def line_warn(s: str) -> None:
    if RICH and console is not None:
        console.print(f"[bold yellow]! {s}[/bold yellow]", highlight=False)
    else:
        p(f"! {s}")

def kv_table(title_str: str, rows: List[Tuple[str, str]]) -> None:
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

# -----------------------------
# Logging
# -----------------------------
logger = logging.getLogger("linuxmole")

def setup_logging(verbose: bool = False, log_file: Optional[str] = None) -> None:
    """
    Configure logging system.

    Args:
        verbose: If True, set DEBUG level. Otherwise INFO.
        log_file: Optional path to log file. If None, only console logging.
    """
    level = logging.DEBUG if verbose else logging.INFO
    handlers = []

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(logging.Formatter('[%(levelname)s] %(message)s'))
    handlers.append(console_handler)

    # File handler (optional)
    if log_file:
        try:
            file_handler = logging.FileHandler(log_file, mode='a', encoding='utf-8')
            file_handler.setFormatter(logging.Formatter(
                '%(asctime)s - [%(levelname)s] - %(name)s - %(message)s'
            ))
            handlers.append(file_handler)
            logger.info(f"Logging to file: {log_file}")
        except Exception as e:
            logger.warning(f"Failed to create log file {log_file}: {e}")

    # Configure root logger
    logging.basicConfig(
        level=level,
        handlers=handlers,
        force=True
    )

    logger.setLevel(level)

    if verbose:
        logger.debug("Verbose logging enabled")

# -----------------------------
# Helpers
# -----------------------------
def which(cmd: str) -> Optional[str]:
    from shutil import which as _which
    return _which(cmd)

def run(cmd: List[str], dry_run: bool, check: bool = False) -> subprocess.CompletedProcess:
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
    logger.debug(f"Capturing output: {' '.join(shlex.quote(x) for x in cmd)}")
    result = subprocess.check_output(cmd, text=True, stderr=subprocess.DEVNULL).strip()
    logger.debug(f"Captured {len(result)} bytes")
    return result

def is_root() -> bool:
    return os.geteuid() == 0

def confirm(msg: str, assume_yes: bool) -> bool:
    if assume_yes:
        return True
    ans = input(f"{msg} [y/N]: ").strip().lower()
    return ans in ("y", "yes")

def human_bytes(n: int) -> str:
    units = ["B", "KB", "MB", "GB", "TB", "PB"]
    f = float(n)
    for u in units:
        if f < 1024.0 or u == units[-1]:
            return f"{int(f)}B" if u == "B" else f"{f:.1f}{u}"
        f /= 1024.0
    return f"{n}B"

def format_size(n: Optional[int], unknown: bool = False) -> str:
    if n is None:
        return "size unavailable"
    s = human_bytes(n)
    return f"{s}+" if unknown else s

def disk_usage_bytes(path: str = "/") -> Optional[Tuple[int, int, int]]:
    try:
        out = capture(["df", "-B1", path])
    except Exception:
        return None
    lines = out.splitlines()
    if len(lines) < 2:
        return None
    parts = lines[1].split()
    if len(parts) < 6:
        return None
    try:
        total = int(parts[1])
        used = int(parts[2])
        avail = int(parts[3])
        return total, used, avail
    except Exception:
        return None

def mem_usage_bytes() -> Optional[Tuple[int, int, int]]:
    try:
        out = capture(["free", "-b"])
    except Exception:
        return None
    for line in out.splitlines():
        if line.lower().startswith("mem:"):
            parts = line.split()
            if len(parts) >= 4:
                try:
                    total = int(parts[1])
                    used = int(parts[2])
                    free = int(parts[3])
                    return total, used, free
                except Exception:
                    return None
    return None

def mem_stats_bytes() -> Optional[Tuple[int, int, int, int]]:
    try:
        out = capture(["free", "-b"])
    except Exception:
        return None
    for line in out.splitlines():
        if line.lower().startswith("mem:"):
            parts = line.split()
            if len(parts) >= 7:
                try:
                    total = int(parts[1])
                    used = int(parts[2])
                    free = int(parts[3])
                    avail = int(parts[6])
                    return total, used, free, avail
                except Exception:
                    return None
    return None

def read_diskstats() -> Dict[str, Tuple[int, int]]:
    res = {}
    try:
        with open("/proc/diskstats", "r", encoding="utf-8") as f:
            for line in f:
                parts = line.split()
                if len(parts) < 14:
                    continue
                name = parts[2]
                if name.startswith(("loop", "ram")):
                    continue
                sectors_read = int(parts[5])
                sectors_written = int(parts[9])
                res[name] = (sectors_read, sectors_written)
    except Exception:
        return {}
    return res

def disk_io_rate() -> Optional[Tuple[float, float]]:
    s1 = read_diskstats()
    if not s1:
        return None
    time.sleep(0.2)
    s2 = read_diskstats()
    if not s2:
        return None
    read_sec = 0
    write_sec = 0
    for k, (r2, w2) in s2.items():
        r1, w1 = s1.get(k, (0, 0))
        read_sec += max(0, r2 - r1)
        write_sec += max(0, w2 - w1)
    # 512 bytes per sector
    read_bps = (read_sec * 512) / 0.2
    write_bps = (write_sec * 512) / 0.2
    return read_bps, write_bps

def read_netdev() -> Dict[str, Tuple[int, int]]:
    res = {}
    try:
        with open("/proc/net/dev", "r", encoding="utf-8") as f:
            for line in f:
                if ":" not in line:
                    continue
                iface, data = line.split(":", 1)
                iface = iface.strip()
                if iface == "lo":
                    continue
                parts = data.split()
                if len(parts) >= 16:
                    rx = int(parts[0])
                    tx = int(parts[8])
                    res[iface] = (rx, tx)
    except Exception:
        return {}
    return res

def net_io_rate() -> Optional[List[Tuple[str, float, float]]]:
    s1 = read_netdev()
    if not s1:
        return None
    time.sleep(0.2)
    s2 = read_netdev()
    if not s2:
        return None
    res = []
    for iface, (rx2, tx2) in s2.items():
        rx1, tx1 = s1.get(iface, (0, 0))
        rx_bps = max(0, rx2 - rx1) / 0.2
        tx_bps = max(0, tx2 - tx1) / 0.2
        res.append((iface, rx_bps, tx_bps))
    res.sort(key=lambda x: (x[1] + x[2]), reverse=True)
    return res

def read_cpu_times() -> Optional[Tuple[int, int]]:
    try:
        with open("/proc/stat", "r", encoding="utf-8") as f:
            line = f.readline()
        parts = line.split()
        if parts[0] != "cpu":
            return None
        nums = [int(x) for x in parts[1:]]
        idle = nums[3] + nums[4] if len(nums) > 4 else nums[3]
        total = sum(nums)
        return total, idle
    except Exception:
        return None

def cpu_usage_percent() -> Optional[float]:
    t1 = read_cpu_times()
    if not t1:
        return None
    time.sleep(0.2)
    t2 = read_cpu_times()
    if not t2:
        return None
    total1, idle1 = t1
    total2, idle2 = t2
    total_delta = total2 - total1
    idle_delta = idle2 - idle1
    if total_delta <= 0:
        return None
    return max(0.0, min(100.0, 100.0 * (1.0 - (idle_delta / total_delta))))

def bar(pct: float, width: int = 24) -> str:
    pct = max(0.0, min(100.0, pct))
    filled = int((pct / 100.0) * width)
    return "█" * filled + "░" * (width - filled)

def add_summary(items: List[Dict], label: str, count: int, size_bytes: Optional[int], size_note: Optional[str] = None, count_display: Optional[str] = None, size_unknown: bool = False, risk: str = "low") -> None:
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
    if not lines:
        return None
    cfg = Path("~/.config/linuxmole").expanduser()
    cfg.mkdir(parents=True, exist_ok=True)
    path = cfg / filename
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path

def print_final_summary(dry_run: bool, total_bytes: int, unknown: bool, items: int, categories: int, log_path: Optional[Path]) -> None:
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

def now_str() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def clear_screen() -> None:
    if sys.stdout.isatty():
        os.system("clear")

def pause(msg: str = "Press Enter to return to the menu...") -> None:
    if sys.stdin.isatty():
        try:
            input(msg)
        except EOFError:
            pass

@contextmanager
def scan_status(msg: str):
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

def maybe_reexec_with_sudo(reason: str) -> None:
    if is_root():
        return
    if which("sudo") and sys.stdin.isatty():
        ans = input(f"{reason} Re-run with sudo? [y/N]: ").strip().lower()
        if ans in ("y", "yes"):
            os.execvp("sudo", ["sudo", sys.executable, os.path.realpath(__file__), *sys.argv[1:]])
    else:
        p(f"[info] {reason} Run with sudo for full access.")

def print_help() -> None:
    print_banner(banner_style="bold cyan", url_style="blue")
    def print_block(title: str, items: List[Tuple[str, str]], pad: Optional[int] = None) -> None:
        p("")
        p(title)
        pad = (max(len(k) for k, _ in items) + 6) if pad is None and items else (pad or 0)
        for key, desc in items:
            if RICH and console is not None:
                console.print(f"[blue]{key.ljust(pad)}[/blue]  {desc}", highlight=False)
            else:
                p(f"{key.ljust(pad)}  {desc}")
        p("")

    commands = [
        ("lm", "Main menu"),
        ("lm status", "Full status (system + docker)"),
        ("lm status system", "System status only"),
        ("lm status docker", "Docker status only"),
        ("lm clean", "Full cleanup (system + docker)"),
        ("lm clean system", "System cleanup only"),
        ("lm clean docker", "Docker cleanup only"),
        ("lm analyze", "Analyze disk usage"),
        ("lm purge", "Clean project build artifacts"),
        ("lm installer", "Find and remove installer files"),
        ("lm whitelist", "Show whitelist config"),
        ("lm uninstall", "Remove LinuxMole from this system"),
        ("lm --version", "Show version"),
        ("lm update", "Update LinuxMole (pipx)"),
    ]
    pad = (max(len(k) for k, _ in commands) + 6) if commands else 0
    print_block("COMMANDS", commands, pad=pad)

    print_block("OPTIONS (clean only)", [
        ("--dry-run", "Preview only, no actions executed"),
        ("--yes", "Assume 'yes' for confirmations"),
        ("-h, --help", "Show help"),
    ], pad=pad)
    p("")
    p("EXAMPLES")
    p("  lm status")
    p("  lm status --paths")
    p("  lm status docker --top-logs 50")
    p("  lm clean --containers --networks --images dangling --dry-run")
    p("  lm clean docker --images unused --yes")
    p("  lm clean docker --truncate-logs-mb 500 --dry-run")
    p("  lm clean system --journal --tmpfiles --apt --dry-run")
    p("  lm clean system --logs --logs-days 14 --dry-run")
    p("  lm clean system --kernels --kernels-keep 2 --dry-run")
    p("  lm analyze --path /var --top 15")
    p("  lm purge")
    p("  lm installer")
    p("  lm whitelist")
    p("  lm --version")
    p("  lm update")

# -----------------------------
# Docker inspection
# -----------------------------
def docker_available() -> bool:
    return which("docker") is not None

def docker_cmd(args: List[str]) -> List[str]:
    return ["docker", *args]

def docker_json_lines(args: List[str]) -> List[Dict]:
    """
    Executes docker command with a JSON-per-line format (via --format '{{json .}}')
    """
    out = capture(docker_cmd(args))
    if not out:
        return []
    lines = out.splitlines()
    res = []
    for ln in lines:
        try:
            res.append(json.loads(ln))
        except Exception:
            # If docker prints non-json, ignore that line
            pass
    return res

def docker_ps_all() -> List[Dict]:
    # includes running + stopped
    return docker_json_lines(["ps", "-a", "--size", "--no-trunc", "--format", "{{json .}}"])

def docker_images_all() -> List[Dict]:
    return docker_json_lines(["images", "-a", "--no-trunc", "--format", "{{json .}}"])

def docker_images_dangling() -> List[Dict]:
    return docker_json_lines(["images", "-f", "dangling=true", "--no-trunc", "--format", "{{json .}}"])

def docker_networks() -> List[Dict]:
    return docker_json_lines(["network", "ls", "--no-trunc", "--format", "{{json .}}"])

def docker_volumes() -> List[Dict]:
    return docker_json_lines(["volume", "ls", "--format", "{{json .}}"])

def docker_networks_dangling() -> List[Dict]:
    return docker_json_lines(["network", "ls", "-f", "dangling=true", "--no-trunc", "--format", "{{json .}}"])

def docker_volumes_dangling() -> List[Dict]:
    return docker_json_lines(["volume", "ls", "-f", "dangling=true", "--format", "{{json .}}"])

def docker_volume_mountpoints(names: List[str]) -> Dict[str, str]:
    if not names:
        return {}
    args = ["volume", "inspect", "--format", "{{.Name}} {{.Mountpoint}}", *names]
    try:
        out = capture(docker_cmd(args))
    except Exception:
        return {}
    res = {}
    for line in out.splitlines():
        parts = line.strip().split(maxsplit=1)
        if len(parts) == 2:
            res[parts[0]] = parts[1]
    return res

def docker_system_df() -> str:
    # human readable
    return capture(docker_cmd(["system", "df"]))

def docker_builder_df() -> str:
    return capture(docker_cmd(["builder", "du"]))

def docker_container_image_ids() -> List[str]:
    """
    Returns image IDs used by any container (running or stopped).
    docker inspect for all containers can be expensive, so we use docker ps -a --format '{{.Image}}' and resolve via images list.
    """
    ps = docker_ps_all()
    # ps entries contain "Image" which is name:tag or image ID; we collect raw and later map.
    used = set()
    for c in ps:
        img = (c.get("Image") or "").strip()
        if img:
            used.add(img)
    return sorted(used)

def compute_unused_images() -> Tuple[List[Dict], List[Dict]]:
    """
    Returns (dangling_images, unused_images_not_dangling)
    - dangling: docker images -f dangling=true
    - unused: images not referenced by any container (by repo:tag match or by ID prefix match)
    """
    all_imgs = docker_images_all()
    dangling = docker_images_dangling()
    used_refs = set(docker_container_image_ids())

    # Build sets for matching
    used_refs_lower = set(x.lower() for x in used_refs)

    unused = []
    for img in all_imgs:
        repo = (img.get("Repository") or "")
        tag = (img.get("Tag") or "")
        img_id = (img.get("ID") or "")
        repotag = f"{repo}:{tag}" if repo and tag and tag != "<none>" and repo != "<none>" else ""
        candidates = set()
        if repotag:
            candidates.add(repotag.lower())
        if img_id:
            candidates.add(img_id.lower())
            # also short id match
            candidates.add(img_id.lower().replace("sha256:", "")[:12])

        # If any candidate matches used_refs entries (which can be name:tag or id/shortid), treat as used
        is_used = False
        for u in used_refs_lower:
            # compare direct or prefix
            if u in candidates:
                is_used = True
                break
            # handle "sha256:..." and short prefixes
            if img_id and (u.startswith(img_id.lower().replace("sha256:", "")[:12]) or img_id.lower().endswith(u)):
                is_used = True
                break
            if repotag and u == repotag.lower():
                is_used = True
                break

        if not is_used:
            # exclude dangling duplicates; we still keep them in unused, but report separately
            unused.append(img)

    # Remove those that are dangling from unused_not_dangling
    dangling_ids = set((d.get("ID") or "") for d in dangling)
    unused_not_dangling = [u for u in unused if (u.get("ID") or "") not in dangling_ids]

    return dangling, unused_not_dangling

# -----------------------------
# Docker preview helpers
# -----------------------------
def docker_stopped_containers() -> List[Dict]:
    stopped = []
    for c in docker_ps_all():
        state = (c.get("State") or "").lower()
        if state != "running":
            stopped.append(c)
    return stopped

def cap_containers(cs: List[Dict], n: int) -> List[List[str]]:
    rows = []
    for it in cs[:n]:
        rows.append([
            (it.get("ID") or "")[:12],
            (it.get("Names") or ""),
            (it.get("Status") or ""),
            (it.get("Size") or ""),
        ])
    return rows

def cap_networks(nets: List[Dict], n: int) -> List[List[str]]:
    rows = []
    for it in nets[:n]:
        rows.append([
            (it.get("ID") or "")[:12],
            (it.get("Name") or ""),
            (it.get("Driver") or ""),
        ])
    return rows

def cap_imgs(imgs: List[Dict], n: int) -> List[List[str]]:
    rows = []
    for it in imgs[:n]:
        rows.append([
            (it.get("ID") or "")[:19],
            (it.get("Repository") or ""),
            (it.get("Tag") or ""),
            (it.get("Size") or ""),
            (it.get("CreatedSince") or ""),
        ])
    return rows

# -----------------------------
# Size parsing and summaries
# -----------------------------
_SIZE_RE = re.compile(r"^\s*([0-9]+(?:\.[0-9]+)?)\s*([KMGTP]?i?B)?\s*$", re.IGNORECASE)

def parse_size_to_bytes(s: str) -> Optional[int]:
    if not s:
        return None
    m = _SIZE_RE.match(s)
    if not m:
        return None
    val = float(m.group(1))
    unit = (m.group(2) or "B").upper()
    factors = {
        "B": 1,
        "KB": 1000,
        "MB": 1000 ** 2,
        "GB": 1000 ** 3,
        "TB": 1000 ** 4,
        "PB": 1000 ** 5,
        "KIB": 1024,
        "MIB": 1024 ** 2,
        "GIB": 1024 ** 3,
        "TIB": 1024 ** 4,
        "PIB": 1024 ** 5,
    }
    if unit not in factors:
        return None
    return int(val * factors[unit])

def parse_journal_usage_bytes(s: str) -> Optional[int]:
    m = re.search(r"([0-9]+(?:\.[0-9]+)?\s*[KMGTP]i?B)", s, re.IGNORECASE)
    if not m:
        return None
    return parse_size_to_bytes(m.group(1))

def sum_image_sizes(imgs: List[Dict]) -> int:
    total = 0
    for it in imgs:
        size_str = (it.get("Size") or "").strip()
        b = parse_size_to_bytes(size_str)
        if b is not None:
            total += b
    return total

def parse_container_size(size_str: str) -> Optional[int]:
    if not size_str:
        return None
    first = size_str.split()[0]
    return parse_size_to_bytes(first)

def sum_container_sizes(containers: List[Dict]) -> Tuple[int, int]:
    total = 0
    unknown = 0
    for it in containers:
        size_str = (it.get("Size") or "").strip()
        b = parse_container_size(size_str)
        if b is None:
            unknown += 1
        else:
            total += b
    return total, unknown

def du_size(path: str) -> Optional[str]:
    if not which("du"):
        return None
    try:
        out = capture(["du", "-sh", path])
        return out.split()[0] if out else None
    except Exception:
        return None

def du_bytes(path: str) -> Optional[int]:
    if not which("du"):
        return None
    try:
        out = capture(["du", "-sb", path])
        if not out:
            return None
        return int(out.split()[0])
    except Exception:
        return None

def apt_autoremove_count() -> Optional[int]:
    if not which("apt-get"):
        return None
    try:
        out = capture(["apt-get", "-s", "autoremove"])
    except Exception:
        return None
    count = 0
    for line in out.splitlines():
        if line.startswith("Remv "):
            count += 1
    return count

def list_installed_kernels() -> List[Tuple[str, str]]:
    if not which("dpkg-query"):
        return []
    try:
        out = capture(["dpkg-query", "-W", "-f", "${Package} ${Version}\n", "linux-image-[0-9]*"])
    except Exception:
        return []
    res = []
    for line in out.splitlines():
        parts = line.split()
        if len(parts) >= 2:
            res.append((parts[0], parts[1]))
    return res

def kernel_version_from_pkg(pkg: str) -> Optional[str]:
    if not pkg.startswith("linux-image-"):
        return None
    return pkg.replace("linux-image-", "", 1)

def sort_versions_dpkg(versions: List[str]) -> List[str]:
    if not which("dpkg"):
        return versions
    def _cmp(a: str, b: str) -> int:
        if a == b:
            return 0
        try:
            subprocess.check_call(["dpkg", "--compare-versions", a, "gt", b])
            return 1
        except Exception:
            return -1
    return sorted(versions, key=cmp_to_key(_cmp))

def kernel_cleanup_candidates(keep: int = 2) -> List[str]:
    current = capture(["uname", "-r"])
    pkgs = list_installed_kernels()
    versions = []
    by_version = {}
    for pkg, ver in pkgs:
        kv = kernel_version_from_pkg(pkg)
        if not kv:
            continue
        versions.append(kv)
        by_version[kv] = pkg
    if not versions:
        return []
    versions_sorted = sort_versions_dpkg(versions)
    keep_set = set(versions_sorted[-keep:])
    keep_set.add(current)
    candidates = [by_version[v] for v in versions_sorted if v not in keep_set]
    return candidates

def kernel_pkg_size_bytes(pkgs: List[str]) -> Optional[int]:
    if not pkgs or not which("dpkg-query"):
        return None
    total = 0
    for pkg in pkgs:
        try:
            out = capture(["dpkg-query", "-W", "-f", "${Installed-Size}", pkg])
            total += int(out.strip()) * 1024
        except Exception:
            return None
    return total

def top_processes(sort_key: str = "-%cpu", limit: int = 5) -> List[List[str]]:
    if not which("ps"):
        return []
    try:
        out = capture(["ps", "-eo", "pid,comm,%cpu,%mem", f"--sort={sort_key}"])
    except Exception:
        return []
    rows = []
    for line in out.splitlines()[1:limit + 1]:
        parts = line.split(None, 3)
        if len(parts) >= 4:
            rows.append(parts)
    return rows

def config_dir() -> Path:
    return Path("~/.config/linuxmole").expanduser()

def whitelist_path() -> Path:
    return config_dir() / "whitelist.txt"

def purge_paths_file() -> Path:
    return config_dir() / "purge_paths"

def config_file_path() -> Path:
    return config_dir() / "config.toml"

def default_config() -> Dict[str, Any]:
    """Return default configuration."""
    return {
        "whitelist": {
            "auto_protect_system": True,
            "patterns": [
                "/home/*/.ssh/*",
                "/home/*/.gnupg/*",
                "/etc/passwd",
                "/etc/shadow",
                "/etc/fstab",
                "/boot/*",
                "/sys/*",
                "/proc/*"
            ]
        },
        "clean": {
            "auto_confirm": False,
            "preserve_recent_days": 7,
            "default_journal_time": "3d",
            "default_journal_size": "500M"
        },
        "paths": {
            "purge_paths": [
                "~/Projects",
                "~/GitHub",
                "~/dev",
                "~/work"
            ],
            "analyze_default": "."
        },
        "optimize": {
            "auto_database": True,
            "auto_network": True,
            "auto_services": True,
            "auto_clear_cache": False
        },
        "tui": {
            "auto_install": True
        }
    }

def load_config() -> Dict[str, Any]:
    """Load configuration from config.toml or return defaults."""
    config_path = config_file_path()

    if not config_path.exists():
        logger.debug("Config file not found, using defaults")
        return default_config()

    if tomllib is None:
        logger.warning("TOML library not available, using defaults")
        return default_config()

    try:
        with open(config_path, "rb") as f:
            config = tomllib.load(f)
        logger.debug(f"Loaded config from {config_path}")
        return config
    except Exception as e:
        logger.error(f"Error loading config: {e}")
        return default_config()

def save_config(config: Dict[str, Any]) -> bool:
    """Save configuration to config.toml."""
    config_path = config_file_path()

    try:
        # Ensure config directory exists
        config_path.parent.mkdir(parents=True, exist_ok=True)

        # Convert dict to TOML string manually (simple implementation)
        lines = []
        for section, values in config.items():
            lines.append(f"[{section}]")
            for key, value in values.items():
                if isinstance(value, bool):
                    lines.append(f"{key} = {str(value).lower()}")
                elif isinstance(value, (int, float)):
                    lines.append(f"{key} = {value}")
                elif isinstance(value, str):
                    lines.append(f'{key} = "{value}"')
                elif isinstance(value, list):
                    # Format list
                    formatted_items = []
                    for item in value:
                        if isinstance(item, str):
                            formatted_items.append(f'"{item}"')
                        else:
                            formatted_items.append(str(item))
                    lines.append(f"{key} = [{', '.join(formatted_items)}]")
            lines.append("")  # Empty line between sections

        config_path.write_text("\n".join(lines), encoding="utf-8")
        logger.info(f"Saved config to {config_path}")
        return True
    except Exception as e:
        logger.error(f"Error saving config: {e}")
        return False

def load_whitelist() -> List[str]:
    path = whitelist_path()
    if not path.exists():
        return []
    patterns = []
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        patterns.append(os.path.expanduser(line))
    return patterns

def is_whitelisted(path: str, patterns: List[str]) -> bool:
    for pat in patterns:
        if fnmatch.fnmatch(path, pat):
            return True
    return False

def ensure_config_files() -> None:
    cfg = config_dir()
    cfg.mkdir(parents=True, exist_ok=True)
    if not whitelist_path().exists():
        whitelist_path().write_text("# Add glob patterns to protect paths\n", encoding="utf-8")
    if not purge_paths_file().exists():
        purge_paths_file().write_text("# One path per line\n", encoding="utf-8")

def load_purge_paths() -> List[str]:
    ensure_config_files()
    path = purge_paths_file()
    res = []
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        res.append(os.path.expanduser(line))
    if not res:
        res = [str(Path("~/Projects").expanduser()),
               str(Path("~/GitHub").expanduser()),
               str(Path("~/dev").expanduser()),
               str(Path("~/work").expanduser())]
    return res

def size_path_bytes(path: Path) -> Optional[int]:
    return du_bytes(str(path))

def list_installer_files() -> List[Tuple[str, int]]:
    exts = (".deb", ".rpm", ".AppImage", ".run", ".tar.gz", ".tgz", ".zip", ".iso")
    locations = [Path("~/Downloads").expanduser(), Path("~/Desktop").expanduser()]
    res: List[Tuple[str, int]] = []
    for base in locations:
        if not base.exists():
            continue
        for p in base.rglob("*"):
            if not p.is_file():
                continue
            name = p.name
            if name.endswith(exts):
                try:
                    res.append((str(p), p.stat().st_size))
                except Exception:
                    continue
    res.sort(key=lambda x: x[1], reverse=True)
    return res

def systemctl_failed_units() -> Optional[List[str]]:
    if not which("systemctl"):
        return None
    try:
        out = capture(["systemctl", "--failed", "--no-legend", "--no-pager"])
    except Exception:
        return None
    units = []
    for line in out.splitlines():
        parts = line.split()
        if len(parts) >= 4 and parts[2].lower() == "failed":
            units.append(parts[0])
    return units

def reboot_required() -> bool:
    return Path("/var/run/reboot-required").exists()

def find_log_candidates(days: int) -> List[Tuple[str, int]]:
    base = Path("/var/log")
    if not base.exists():
        return []
    cutoff = time.time() - (days * 86400)
    patterns = (".gz", ".old", ".1", ".2", ".3", ".4", ".5", ".6", ".7", ".8", ".9")
    res: List[Tuple[str, int]] = []
    for path in base.rglob("*"):
        if not path.is_file():
            continue
        name = path.name
        if not (name.endswith(patterns) or re.search(r"\.\d+\.gz$", name)):
            continue
        try:
            st = path.stat()
        except Exception:
            continue
        if st.st_mtime < cutoff:
            res.append((str(path), st.st_size))
    res.sort(key=lambda x: x[1], reverse=True)
    return res

def parse_path_entries(raw: str) -> List[str]:
    return [p for p in raw.split(":") if p]

def analyze_paths() -> Dict[str, List[str]]:
    env_path = os.environ.get("PATH", "")
    entries = [os.path.expanduser(os.path.expandvars(p)) for p in parse_path_entries(env_path)]
    seen = set()
    dup = []
    missing = []
    for pth in entries:
        if pth in seen:
            dup.append(pth)
        else:
            seen.add(pth)
        if not os.path.isdir(pth):
            missing.append(pth)

    rc_files = [
        Path("~/.zshrc").expanduser(),
        Path("~/.bashrc").expanduser(),
        Path("~/.profile").expanduser(),
        Path("~/.bash_profile").expanduser(),
        Path("/etc/profile"),
        Path("/etc/zshrc"),
    ]
    rc_hits = []
    for fp in rc_files:
        if not fp.exists():
            continue
        try:
            for line in fp.read_text(encoding="utf-8", errors="ignore").splitlines():
                if "PATH=" in line or "export PATH" in line:
                    rc_hits.append(f"{fp}: {line.strip()}")
        except Exception:
            continue

    return {
        "entries": entries,
        "duplicates": dup,
        "missing": missing,
        "rc_hits": rc_hits,
    }

# -----------------------------
# Docker logs (json-file)
# -----------------------------
def docker_default_log_dir() -> Path:
    return Path("/var/lib/docker/containers")

def can_read_docker_logs() -> bool:
    base = docker_default_log_dir()
    try:
        return base.exists() and os.access(base, os.R_OK | os.X_OK)
    except Exception:
        return False

def docker_logs_dir_exists() -> bool:
    base = docker_default_log_dir()
    try:
        return base.exists()
    except Exception:
        return False

def docker_container_log_paths() -> List[Tuple[str, Path]]:
    """
    Returns list of (container_id, log_path) for json-file logs, if present.
    """
    base = docker_default_log_dir()
    res = []
    try:
        if not base.exists():
            return res
    except PermissionError:
        return res
    try:
        for d in base.iterdir():
            if not d.is_dir():
                continue
            cid = d.name
            logp = d / f"{cid}-json.log"
            if logp.exists():
                res.append((cid, logp))
    except PermissionError:
        return res
    return res

def stat_logs(top_n: int = 20) -> List[Tuple[str, Path, int]]:
    items = []
    for cid, logp in docker_container_log_paths():
        try:
            sz = logp.stat().st_size
            items.append((cid, logp, sz))
        except Exception:
            pass
    items.sort(key=lambda x: x[2], reverse=True)
    return items[:top_n]

def total_logs_size() -> Tuple[int, int]:
    total = 0
    count = 0
    for _, logp in docker_container_log_paths():
        try:
            total += logp.stat().st_size
            count += 1
        except Exception:
            pass
    return total, count

def list_all_logs() -> List[Tuple[str, Path, int]]:
    items = []
    for cid, logp in docker_container_log_paths():
        try:
            items.append((cid, logp, logp.stat().st_size))
        except Exception:
            pass
    return items

def truncate_file(path: Path, dry_run: bool) -> None:
    if dry_run:
        p(f"[dry-run] truncate -s 0 {path}")
        return
    try:
        with open(path, "w", encoding="utf-8"):
            pass
        p(f"[ok] truncated {path}")
    except Exception as e:
        p(f"[error] truncate {path}: {e}")

# -----------------------------
# Plans
# -----------------------------
@dataclass
class Action:
    label: str
    cmd: List[str]
    root: bool = False

def show_plan(actions: List[Action], heading: str) -> None:
    rows = []
    for i, a in enumerate(actions, 1):
        rows.append([str(i), a.label + (" (root)" if a.root else ""), " ".join(shlex.quote(x) for x in a.cmd)])
    table(heading, ["#", "Action", "Command"], rows)

def exec_actions(actions: List[Action], dry_run: bool) -> None:
    for a in actions:
        if a.root and not is_root():
            if which("sudo"):
                run(["sudo", *a.cmd], dry_run=dry_run, check=False)
            else:
                p(f"[skip] requires root and sudo is not available: {a.label}")
        else:
            run(a.cmd, dry_run=dry_run, check=False)

# -----------------------------
# Commands
# -----------------------------
def cmd_status_system(_: argparse.Namespace) -> None:
    section("System status")
    with scan_status("Scanning system..."):
        rows = [("Timestamp", now_str())]
        try:
            rows.append(("Uptime", capture(["uptime", "-p"])))
        except Exception:
            rows.append(("Uptime", "n/a"))
        try:
            rows.append(("Load", capture(["cat", "/proc/loadavg"])))
        except Exception:
            rows.append(("Load", "n/a"))
        mem_b = mem_usage_bytes()
        disk_b = disk_usage_bytes("/")
        mem_stats = mem_stats_bytes()
    kv_table("Summary", rows)
    if mem_b and disk_b:
        mem_total, mem_used, _ = mem_b
        disk_total, disk_used, disk_avail = disk_b
        line_do(f"System: RAM {format_size(mem_used)}/{format_size(mem_total)} | Disk {format_size(disk_used)}/{format_size(disk_total)} | Free {format_size(disk_avail)}")

    if mem_stats:
        total, used, free, avail = mem_stats
        table("Memory", ["Total", "Used", "Free", "Available"], [[
            format_size(total), format_size(used), format_size(free), format_size(avail)
        ]])

    section("Health snapshot")
    with scan_status("Scanning CPU/memory/disk..."):
        cpu = cpu_usage_percent()
        mem_b = mem_usage_bytes()
        disk_b = disk_usage_bytes("/")
    if cpu is not None:
        line_do(f"{'CPU':<7}{bar(cpu)}  {cpu:5.1f}%")
    else:
        line_skip("CPU usage unavailable")
    if mem_b:
        total, used, _ = mem_b
        pct = 0.0 if total == 0 else (used / total) * 100.0
        line_do(f"{'Memory':<7}{bar(pct)}  {pct:5.1f}% ({format_size(used)}/{format_size(total)})")
    else:
        line_skip("Memory usage unavailable")
    if disk_b:
        total, used, _ = disk_b
        pct = 0.0 if total == 0 else (used / total) * 100.0
        line_do(f"{'Disk':<7}{bar(pct)}  {pct:5.1f}% ({format_size(used)}/{format_size(total)})")
    else:
        line_skip("Disk usage unavailable")

    section("Health score")
    score = 100
    if cpu is not None:
        if cpu > 90:
            score -= 30
        elif cpu > 75:
            score -= 15
    if mem_b:
        total, used, _ = mem_b
        pct = 0.0 if total == 0 else (used / total) * 100.0
        if pct > 90:
            score -= 30
        elif pct > 80:
            score -= 15
    if disk_b:
        total, used, _ = disk_b
        pct = 0.0 if total == 0 else (used / total) * 100.0
        if pct > 90:
            score -= 30
        elif pct > 85:
            score -= 15
    score = max(0, min(100, score))
    if RICH and console is not None:
        color = "green" if score >= 80 else "yellow" if score >= 50 else "red"
        console.print(f"Health ● {score}", style=color, highlight=False)
    else:
        p(f"Health ● {score}")

    section("Disk I/O")
    with scan_status("Scanning disk I/O..."):
        io = disk_io_rate()
    if io:
        read_bps, write_bps = io
        line_do(f"Read  {format_size(int(read_bps))}/s")
        line_do(f"Write {format_size(int(write_bps))}/s")
    else:
        line_skip("Disk I/O unavailable")

    section("Network")
    with scan_status("Scanning network..."):
        net = net_io_rate()
    if net:
        rows = []
        for iface, rx, tx in net[:5]:
            rows.append([iface, f"{format_size(int(rx))}/s", f"{format_size(int(tx))}/s"])
        table("Top interfaces", ["Iface", "Down", "Up"], rows)
    else:
        line_skip("Network I/O unavailable")

    section("Disk")
    with scan_status("Scanning disk..."):
        try:
            out = subprocess.check_output(["df", "-h", "-x", "tmpfs", "-x", "devtmpfs"], text=True)
        except Exception:
            out = ""
    if out:
        p(out)
    else:
        line_warn("Could not read df -h")

    section("Inodes")
    with scan_status("Scanning inodes..."):
        try:
            out = subprocess.check_output(["df", "-i", "-x", "tmpfs", "-x", "devtmpfs"], text=True)
        except Exception:
            out = ""
    if out:
        p(out)
    else:
        line_warn("Could not read df -i")

    section("Journald")
    if which("journalctl"):
        with scan_status("Scanning journald..."):
            try:
                out = capture(["journalctl", "--disk-usage"])
            except Exception:
                out = ""
        if out:
            line_do(f"Disk usage: {out}")
        else:
            line_warn("Could not read journald usage")
    else:
        line_skip("journalctl not available")

    section("System health")
    with scan_status("Scanning failed units..."):
        failed = systemctl_failed_units()
    if failed is None:
        line_skip("systemctl not available")
    elif not failed:
        line_ok("No failed units")
    else:
        line_warn(f"Failed units: {len(failed)}")
        for unit in failed[:10]:
            line_do(unit)
        if len(failed) > 10:
            line_do(f"... and {len(failed) - 10} more")

    section("Top processes")
    cpu_top = top_processes("-%cpu", 5)
    mem_top = top_processes("-%mem", 5)
    if cpu_top:
        table("Top CPU", ["PID", "Command", "CPU%", "MEM%"], cpu_top)
    else:
        line_skip("Top CPU not available")
    if mem_top:
        table("Top Memory", ["PID", "Command", "CPU%", "MEM%"], mem_top)
    else:
        line_skip("Top memory not available")

    section("Packages")
    with scan_status("Scanning APT cache..."):
        apt_cache = du_size("/var/cache/apt/archives")
    if apt_cache:
        line_do(f"APT cache: {apt_cache}")
    else:
        line_skip("APT cache size not available")
    with scan_status("Scanning autoremove candidates..."):
        count = apt_autoremove_count()
    if count is None:
        line_skip("Autoremove count not available")
    else:
        line_do(f"Autoremove candidates: {count}")

    section("Kernel")
    with scan_status("Scanning kernels..."):
        candidates = kernel_cleanup_candidates()
    if candidates:
        line_warn(f"Old kernels detected: {len(candidates)} (clean with --kernels)")
        for pkg in candidates[:10]:
            line_do(pkg)
        if len(candidates) > 10:
            line_do(f"... and {len(candidates) - 10} more")
    else:
        line_ok("No old kernels detected")

    section("Reboot")
    if reboot_required():
        line_warn("Reboot required")
    else:
        line_ok("No reboot required")

def cmd_status_all(args: argparse.Namespace) -> None:
    cmd_status_system(args)
    if getattr(args, "paths", False):
        section("PATH audit")
        with scan_status("Scanning PATH entries..."):
            res = analyze_paths()
        line_do(f"Entries: {len(res['entries'])}")
        if res["duplicates"]:
            line_warn(f"Duplicates: {len(res['duplicates'])}")
            for pth in res["duplicates"][:10]:
                line_do(pth)
        else:
            line_ok("No duplicates")
        if res["missing"]:
            line_warn(f"Missing directories: {len(res['missing'])}")
            for pth in res["missing"][:10]:
                line_do(pth)
        else:
            line_ok("No missing directories")
        if res["rc_hits"]:
            line_do(f"RC PATH entries: {len(res['rc_hits'])}")
            for line in res["rc_hits"][:10]:
                line_do(line)
        else:
            line_ok("No PATH entries found in rc files")
    cmd_docker_status(args)
    section("Status summary")
    rows = []
    mem_b = mem_usage_bytes()
    disk_b = disk_usage_bytes("/")
    failed = systemctl_failed_units()
    autoremove = apt_autoremove_count()
    if mem_b:
        total, used, _ = mem_b
        rows.append(["Memory", f"{format_size(used)}/{format_size(total)}"])
    if disk_b:
        total, used, avail = disk_b
        rows.append(["Disk", f"{format_size(used)}/{format_size(total)} | Free {format_size(avail)}"])
    if failed is None:
        rows.append(["Failed units", "n/a"])
    else:
        rows.append(["Failed units", str(len(failed))])
    if autoremove is None:
        rows.append(["Autoremove candidates", "n/a"])
    else:
        rows.append(["Autoremove candidates", str(autoremove)])
    if reboot_required():
        rows.append(["Reboot", "Required"])
    else:
        rows.append(["Reboot", "Not required"])
    if docker_available():
        try:
            containers = docker_ps_all()
            running = [c for c in containers if (c.get("State") or "").lower() == "running"]
            images = docker_images_all()
            volumes = docker_volumes()
            rows.append(["Docker", f"{len(running)}/{len(containers)} running | {len(images)} images | {len(volumes)} volumes"])
        except Exception:
            rows.append(["Docker", "n/a"])
    if rows:
        table("Summary", ["Item", "Value"], rows)

def cmd_docker_status(args: argparse.Namespace) -> None:
    if not docker_available():
        line_warn("Docker is not installed or not accessible.")
        return
    if not is_root() and docker_logs_dir_exists() and not can_read_docker_logs():
        maybe_reexec_with_sudo("Permissions are required to read Docker logs.")

    with scan_status("Scanning Docker summary..."):
        containers = docker_ps_all()
        running = [c for c in containers if (c.get("State") or "").lower() == "running"]
        images = docker_images_all()
        volumes = docker_volumes()
    line_do(f"Docker: containers {len(running)}/{len(containers)} | images {len(images)} | volumes {len(volumes)}")

    section("Docker system df")
    with scan_status("Scanning Docker system df..."):
        try:
            out = docker_system_df()
        except Exception:
            out = ""
    if out:
        p(out)
    else:
        line_warn("Could not read docker system df")

    section("Docker builder du")
    with scan_status("Scanning Docker builder du..."):
        try:
            out = docker_builder_df()
        except Exception:
            out = ""
    if out:
        p(out)
    else:
        line_warn("Could not read docker builder du")

    section("Dangling images")
    with scan_status("Scanning images..."):
        dangling, unused = compute_unused_images()
    line_do(f"Dangling (orphaned layers): {len(dangling)}")
    line_do(f"Unused (not used by any container): {len(unused)}")
    if dangling:
        table("Dangling images (top 20)", ["ID", "Repo", "Tag", "Size", "Age"], cap_imgs(dangling, 20))
    if unused:
        table("Unused images (top 20)", ["ID", "Repo", "Tag", "Size", "Age"], cap_imgs(unused, 20))

    section("Docker logs")
    if can_read_docker_logs():
        with scan_status("Scanning Docker logs..."):
            logs = stat_logs(top_n=args.top_logs)
        if logs:
            rows = []
            for cid, lp, sz in logs:
                rows.append([cid[:12], human_bytes(sz), str(lp)])
            table(f"Docker logs (top {args.top_logs})", ["Container", "Size", "Path"], rows)
        else:
            line_ok("Nothing to show")
    else:
        line_warn("No permissions to read Docker logs")

def cmd_docker_clean(args: argparse.Namespace) -> None:
    apply_default_clean_flags(args, "docker")
    if not docker_available():
        p("Docker is not installed or not accessible.")
        return

    if not any([args.containers, args.networks, args.volumes, args.builder, args.system_prune, args.truncate_logs_mb]) and args.images == "off":
        line_warn("No Docker actions selected. Use --help for options.")
        return

    section("Docker clean")
    if args.dry_run:
        line_do("Dry Run Mode - Preview only, no deletions")

    if args.truncate_logs_mb is not None and not is_root() and docker_logs_dir_exists() and not can_read_docker_logs():
        maybe_reexec_with_sudo("Permissions are required to truncate Docker logs.")

    actions: List[Action] = []

    # 1) stopped containers
    if args.containers:
        actions.append(Action(
            "Remove stopped containers",
            docker_cmd(["container", "prune", "-f"]),
            root=False
        ))

    # 2) networks
    if args.networks:
        actions.append(Action(
            "Remove dangling networks (not used)",
            docker_cmd(["network", "prune", "-f"]),
            root=False
        ))

    # 3) images
    if args.images in ("dangling", "unused", "all"):
        if args.images == "dangling":
            actions.append(Action("Remove dangling images", docker_cmd(["image", "prune", "-f"]), root=False))
        elif args.images == "unused":
            # removes unused images (not just dangling)
            actions.append(Action("Remove unused images (not referenced by containers)", docker_cmd(["image", "prune", "-a", "-f"]), root=False))
        else:
            # all = aggressive, but still not volumes
            actions.append(Action("Remove unused images (includes dangling and unreferenced)", docker_cmd(["image", "prune", "-a", "-f"]), root=False))

    # 4) volumes
    if args.volumes:
        actions.append(Action(
            "Remove dangling volumes (not used)",
            docker_cmd(["volume", "prune", "-f"]),
            root=False
        ))

    # 5) builder cache
    if args.builder:
        # builder prune can be aggressive; allow --builder-all
        cmd = ["builder", "prune", "-f"]
        if args.builder_all:
            cmd.append("--all")
        actions.append(Action("Clean builder cache", docker_cmd(cmd), root=False))

    # 6) system prune (optional)
    if args.system_prune:
        cmd = ["system", "prune", "-f"]
        if args.system_prune_all:
            cmd.append("-a")
        if args.system_prune_volumes:
            cmd.append("--volumes")
        actions.append(Action("Docker system prune (selected flags)", docker_cmd(cmd), root=False))

    # 7) logs truncation (optional)
    # NOTE: this is not a docker command; it truncates json-file logs on disk.
    # For safety: only if explicitly requested.
    do_truncate = args.truncate_logs_mb is not None

    if not actions and not do_truncate:
        line_warn("No actions selected. Use --help for options.")
        return

    if actions:
        section("Plan")
        show_plan(actions, "Docker Plan")

    detail_lines: List[str] = []
    summary_items: List[Dict] = []

    section("Preview")
    if args.containers:
        with scan_status("Scanning stopped containers..."):
            stopped = docker_stopped_containers()
        size_b, unknown = sum_container_sizes(stopped)
        line_do(f"Stopped containers: {len(stopped)} ({format_size(size_b, unknown)} reported by Docker)")
        add_summary(summary_items, "Stopped containers", len(stopped), size_b, "reported by Docker", size_unknown=unknown, risk="low")
        for it in stopped:
            detail_lines.append(f"container\t{it.get('ID','')}\t{it.get('Names','')}\t{it.get('Status','')}\t{it.get('Size','')}")
        if stopped:
            table("Candidates: stopped containers (top 20)", ["ID", "Name", "Status", "Size"], cap_containers(stopped, 20))
        else:
            line_ok("Nothing to clean")

    if args.networks:
        with scan_status("Scanning dangling networks..."):
            nets = docker_networks_dangling()
        line_do(f"Dangling networks: {len(nets)}")
        add_summary(summary_items, "Dangling networks", len(nets), None, risk="low")
        for it in nets:
            detail_lines.append(f"network\t{it.get('ID','')}\t{it.get('Name','')}\t{it.get('Driver','')}")
        if nets:
            table("Candidates: dangling networks (top 20)", ["ID", "Name", "Driver"], cap_networks(nets, 20))
        else:
            line_ok("Nothing to clean")

    if args.volumes:
        with scan_status("Scanning dangling volumes..."):
            vols = docker_volumes_dangling()
        size_b = 0
        unknown = 0
        rows = []
        if vols:
            names = [v.get("Name") or "" for v in vols if v.get("Name")]
            mountpoints = docker_volume_mountpoints(names)
            for name in names:
                mp = mountpoints.get(name)
                if not mp:
                    unknown += 1
                    continue
                b = du_bytes(mp)
                if b is None:
                    unknown += 1
                else:
                    size_b += b
            for v in vols[:20]:
                name = v.get("Name") or ""
                mp = mountpoints.get(name, "")
                rows.append([name, (v.get("Driver") or ""), mp])
                detail_lines.append(f"volume\t{name}\t{mp}")
        line_do(f"Dangling volumes: {len(vols)} ({format_size(size_b, unknown)})")
        add_summary(summary_items, "Dangling volumes", len(vols), size_b, size_unknown=unknown > 0, risk="high")
        if rows:
            table("Candidates: dangling volumes (top 20)", ["Name", "Driver", "Mountpoint"], rows)
        else:
            line_ok("Nothing to clean")

    if args.images in ("dangling", "unused", "all"):
        with scan_status("Scanning images..."):
            dangling, unused = compute_unused_images()
        if args.images == "dangling":
            size_b = sum_image_sizes(dangling)
            line_do(f"Dangling images: {len(dangling)} ({format_size(size_b)})")
            add_summary(summary_items, "Dangling images", len(dangling), size_b, risk="low")
            for it in dangling:
                detail_lines.append(f"image\t{it.get('ID','')}\t{it.get('Repository','')}:{it.get('Tag','')}\t{it.get('Size','')}")
            if dangling:
                table("Candidates: dangling images (top 20)", ["ID", "Repo", "Tag", "Size", "Age"], cap_imgs(dangling, 20))
            else:
                line_ok("Nothing to clean")
        else:
            size_b = sum_image_sizes(dangling) + sum_image_sizes(unused)
            line_do(f"Unused images: {len(dangling) + len(unused)} ({format_size(size_b)})")
            add_summary(summary_items, "Unused images", len(dangling) + len(unused), size_b, risk="med")
            for it in dangling + unused:
                detail_lines.append(f"image\t{it.get('ID','')}\t{it.get('Repository','')}:{it.get('Tag','')}\t{it.get('Size','')}")
            if dangling:
                table("Candidates: dangling images (top 20)", ["ID", "Repo", "Tag", "Size", "Age"], cap_imgs(dangling, 20))
            if unused:
                table("Candidates: unused images (top 20)", ["ID", "Repo", "Tag", "Size", "Age"], cap_imgs(unused, 20))
            if not dangling and not unused:
                line_ok("Nothing to clean")

    if args.builder:
        line_do("Builder cache: inspection available via docker builder du")
        add_summary(summary_items, "Builder cache", 0, None, risk="low")
        with scan_status("Scanning Docker builder du..."):
            try:
                out = docker_builder_df()
            except Exception:
                out = ""
        if out:
            p(out)

    if args.system_prune:
        line_do("Docker system prune: inspection available via docker system df")
        add_summary(summary_items, "Docker system prune", 0, None, risk="high")
        with scan_status("Scanning Docker system df..."):
            try:
                out = docker_system_df()
            except Exception:
                out = ""
        if out:
            p(out)

    if do_truncate:
        threshold_bytes = int(args.truncate_logs_mb * 1024 * 1024)
        with scan_status("Scanning Docker logs..."):
            logs = stat_logs(top_n=500)
        to_trunc = [(cid, lp, sz) for (cid, lp, sz) in logs if sz >= threshold_bytes]
        rows = [[cid[:12], human_bytes(sz), str(lp)] for (cid, lp, sz) in to_trunc[:50]]
        if rows:
            table(f"Logs to truncate (>= {args.truncate_logs_mb}MB) [showing up to 50]", ["Container", "Size", "Path"], rows)
            total_logs = sum(sz for _, _, sz in to_trunc)
            add_summary(summary_items, "Docker logs (json-file)", len(to_trunc), total_logs, risk="med")
            for _, lp, sz in to_trunc:
                detail_lines.append(f"log\t{lp}\t{sz}")
        else:
            line_ok(f"No logs >= {args.truncate_logs_mb}MB")
            add_summary(summary_items, "Docker logs (json-file)", 0, 0, risk="med")
    else:
        if can_read_docker_logs():
            with scan_status("Scanning Docker logs..."):
                logs = stat_logs(top_n=20)
            if logs:
                rows = [[cid[:12], human_bytes(sz), str(lp)] for (cid, lp, sz) in logs]
                table("Current logs (top 20)", ["Container", "Size", "Path"], rows)
            total_b, total_count = total_logs_size()
            add_summary(summary_items, "Docker logs (json-file)", total_count, total_b, risk="med")
            for _, lp, sz in list_all_logs():
                detail_lines.append(f"log\t{lp}\t{sz}")
        else:
            line_warn("No permissions to read Docker logs")
            add_summary(summary_items, "Docker logs (json-file)", 0, None, count_display="-", risk="med")

    if summary_items:
        section("Summary")
        render_summary(summary_items)
        section("Risk levels")
        render_risks(summary_items)
    else:
        line_warn("Summary: no actions selected.")

    total_bytes, unknown, total_items, categories = summary_totals(summary_items)
    log_path = write_detail_list(detail_lines, "clean-list.txt")

    if args.dry_run:
        print_final_summary(True, total_bytes, unknown, total_items, categories, log_path)
        return

    if not confirm("Run the plan?", args.yes):
        p("Cancelled.")
        return

    if actions:
        exec_actions(actions, dry_run=args.dry_run)

    if do_truncate:
        threshold_bytes = int(args.truncate_logs_mb * 1024 * 1024)
        # full list (not capped) for truncation
        all_logs = []
        for cid, lp in docker_container_log_paths():
            try:
                sz = lp.stat().st_size
                if sz >= threshold_bytes:
                    all_logs.append((cid, lp, sz))
            except Exception:
                pass
        all_logs.sort(key=lambda x: x[2], reverse=True)
        for cid, lp, sz in all_logs:
            p(f"[log] truncate {cid[:12]} {human_bytes(sz)} {lp}")
            truncate_file(lp, dry_run=args.dry_run)

    print_final_summary(False, total_bytes, unknown, total_items, categories, log_path)

def cmd_clean_system(args: argparse.Namespace) -> None:
    apply_default_clean_flags(args, "system")
    section("Clean system")
    if args.dry_run:
        line_do("Dry Run Mode - Preview only, no deletions")

    if (args.journal or args.tmpfiles or args.apt) and not is_root():
        maybe_reexec_with_sudo("Root permissions are required for clean system.")

    actions: List[Action] = []

    # journald
    if args.journal and which("journalctl"):
        if args.journal_time:
            actions.append(Action(f"Journald vacuum by time (keep {args.journal_time})",
                                  ["journalctl", f"--vacuum-time={args.journal_time}"], root=True))
        if args.journal_size:
            actions.append(Action(f"Journald vacuum by size (cap {args.journal_size})",
                                  ["journalctl", f"--vacuum-size={args.journal_size}"], root=True))

    # tmpfiles
    if args.tmpfiles and which("systemd-tmpfiles"):
        actions.append(Action("systemd-tmpfiles --clean", ["systemd-tmpfiles", "--clean"], root=True))

    # apt
    if args.apt and which("apt-get"):
        actions.append(Action("apt autoremove", ["apt-get", "-y", "autoremove"], root=True))
        actions.append(Action("apt autoclean", ["apt-get", "-y", "autoclean"], root=True))
        actions.append(Action("apt clean", ["apt-get", "clean"], root=True))

    # logs
    if args.logs:
        actions.append(Action(f"Clean rotated logs older than {args.logs_days}d", ["true"], root=True))

    if args.kernels:
        actions.append(Action(f"Remove old kernels (keep {args.kernels_keep})", ["true"], root=True))

    if args.pip_cache:
        actions.append(Action("Clean pip cache", ["true"], root=True))
    if args.npm_cache:
        actions.append(Action("Clean npm cache", ["true"], root=True))
    if args.cargo_cache:
        actions.append(Action("Clean cargo cache", ["true"], root=True))
    if args.go_cache:
        actions.append(Action("Clean Go module cache", ["true"], root=True))
    if args.snap:
        actions.append(Action("Clean old snap revisions", ["true"], root=True))
    if args.flatpak:
        actions.append(Action("Clean unused flatpak runtimes", ["true"], root=True))
    if args.logrotate:
        actions.append(Action("Force logrotate", ["logrotate", "-f", "/etc/logrotate.conf"], root=True))

    if not actions:
        line_warn("Nothing to do (or tools not available).")
        return

    section("Plan")
    show_plan(actions, "System Plan")

    detail_lines: List[str] = []
    summary_items: List[Dict] = []

    section("Preview")
    if args.journal and which("journalctl"):
        with scan_status("Scanning journald..."):
            try:
                usage = capture(["journalctl", "--disk-usage"])
            except Exception:
                usage = ""
        if usage:
            line_do(f"Journald: {usage}")
            size_b = parse_journal_usage_bytes(usage)
            add_summary(summary_items, "Journald", 1, size_b, risk="med")
            detail_lines.append("journald\tjournalctl --disk-usage")
        else:
            line_warn("Could not read journald usage")

    if args.tmpfiles:
        with scan_status("Scanning /tmp and /var/tmp..."):
            tmp_b = du_bytes("/tmp")
            var_tmp_b = du_bytes("/var/tmp")
        tmp_info = f"/tmp: {format_size(tmp_b)} | /var/tmp: {format_size(var_tmp_b)}"
        line_do(f"Tmpfiles: {tmp_info}")
        total_tmp = (tmp_b or 0) + (var_tmp_b or 0)
        unknown = tmp_b is None or var_tmp_b is None
        add_summary(summary_items, "Tmpfiles", 2, total_tmp, size_unknown=unknown, risk="low")
        detail_lines.append("tmpfiles\t/tmp")
        detail_lines.append("tmpfiles\t/var/tmp")

    if args.apt:
        with scan_status("Scanning APT cache..."):
            apt_b = du_bytes("/var/cache/apt/archives")
        line_do(f"APT cache: {format_size(apt_b)}")
        add_summary(summary_items, "APT cache", 1, apt_b, risk="low")
        detail_lines.append("apt\t/var/cache/apt/archives")

    if args.logs:
        with scan_status("Scanning rotated logs..."):
            logs = find_log_candidates(args.logs_days)
        total_logs = sum(sz for _, sz in logs)
        add_summary(summary_items, "Rotated logs", len(logs), total_logs, risk="med")
        if logs:
            for path, sz in logs[:50]:
                detail_lines.append(f"log\t{path}\t{sz}")
            rows = [[Path(p).name, human_bytes(sz), p] for p, sz in logs[:20]]
            table("Rotated logs (top 20)", ["File", "Size", "Path"], rows)
            line_do(f"Rotated logs: {len(logs)} ({format_size(total_logs)})")
        else:
            line_ok("No rotated logs to clean")

    if args.kernels:
        with scan_status("Scanning old kernels..."):
            candidates = kernel_cleanup_candidates(args.kernels_keep)
        size_b = kernel_pkg_size_bytes(candidates)
        add_summary(summary_items, "Old kernels", len(candidates), size_b, risk="high")
        if candidates:
            rows = [[pkg, "", ""] for pkg in candidates[:20]]
            table("Kernel packages to remove (top 20)", ["Package", "Version", "Note"], rows)
            line_do(f"Old kernels: {len(candidates)} ({format_size(size_b)})")
            for pkg in candidates:
                detail_lines.append(f"kernel\t{pkg}")
        else:
            line_ok("No old kernels to clean")

    patterns = load_whitelist()
    def _cache_preview(label: str, path: Path, flag: bool) -> None:
        if not flag:
            return
        if not path.exists():
            line_skip(f"{label}: not found")
            add_summary(summary_items, label, 0, 0, risk="low")
            return
        pstr = str(path)
        if is_whitelisted(pstr, patterns):
            line_skip(f"{label}: whitelisted")
            add_summary(summary_items, label, 0, 0)
            return
        size_b = du_bytes(pstr)
        add_summary(summary_items, label, 1, size_b, risk="low")
        line_do(f"{label}: {format_size(size_b)}")
        detail_lines.append(f"cache\t{pstr}")

    _cache_preview("pip cache", Path("~/.cache/pip").expanduser(), args.pip_cache)
    _cache_preview("npm cache", Path("~/.npm").expanduser(), args.npm_cache)
    _cache_preview("cargo cache", Path("~/.cargo/registry").expanduser(), args.cargo_cache)
    _cache_preview("cargo git", Path("~/.cargo/git").expanduser(), args.cargo_cache)
    _cache_preview("go module cache", Path("~/go/pkg/mod").expanduser(), args.go_cache)

    if args.snap:
        with scan_status("Scanning snap revisions..."):
            candidates = []
            if which("snap"):
                try:
                    out = capture(["snap", "list", "--all"])
                    for line in out.splitlines()[1:]:
                        parts = line.split()
                        if len(parts) >= 6 and parts[5] == "disabled":
                            candidates.append((parts[0], parts[2]))
                except Exception:
                    candidates = []
        add_summary(summary_items, "snap revisions", len(candidates), None, risk="med")
        if candidates:
            rows = [[n, r] for n, r in candidates[:20]]
            table("Snap revisions to remove (top 20)", ["Name", "Rev"], rows)
        else:
            line_ok("No old snap revisions")

    if args.flatpak:
        line_do("Flatpak: will run flatpak uninstall --unused")
        add_summary(summary_items, "flatpak unused", 0, None, risk="med")

    if summary_items:
        section("Summary")
        render_summary(summary_items)
        section("Risk levels")
        render_risks(summary_items)
    else:
        line_warn("Summary: no actions selected.")

    total_bytes, unknown, total_items, categories = summary_totals(summary_items)
    log_path = write_detail_list(detail_lines, "clean-list.txt")

    if args.dry_run:
        print_final_summary(True, total_bytes, unknown, total_items, categories, log_path)
        return

    if not confirm("Run the plan?", args.yes):
        p("Cancelled.")
        return

    patterns = load_whitelist()
    if args.logs:
        logs = find_log_candidates(args.logs_days)
        for path, _ in logs:
            if is_whitelisted(path, patterns):
                continue
            run(["rm", "-f", path], dry_run=args.dry_run, check=False)

    if args.kernels:
        candidates = kernel_cleanup_candidates(args.kernels_keep)
        if candidates:
            run(["apt-get", "-y", "purge", *candidates], dry_run=args.dry_run, check=False)

    def _rm_cache(path: Path, flag: bool) -> None:
        if not flag:
            return
        pstr = str(path)
        if is_whitelisted(pstr, patterns):
            return
        if path.exists():
            run(["rm", "-rf", pstr], dry_run=args.dry_run, check=False)

    _rm_cache(Path("~/.cache/pip").expanduser(), args.pip_cache)
    _rm_cache(Path("~/.npm").expanduser(), args.npm_cache)
    _rm_cache(Path("~/.cargo/registry").expanduser(), args.cargo_cache)
    _rm_cache(Path("~/.cargo/git").expanduser(), args.cargo_cache)
    _rm_cache(Path("~/go/pkg/mod").expanduser(), args.go_cache)

    if args.snap and which("snap"):
        try:
            out = capture(["snap", "list", "--all"])
            for line in out.splitlines()[1:]:
                parts = line.split()
                if len(parts) >= 6 and parts[5] == "disabled":
                    run(["snap", "remove", parts[0], "--revision", parts[2]], dry_run=args.dry_run, check=False)
        except Exception:
            pass

    if args.flatpak and which("flatpak"):
        run(["flatpak", "uninstall", "-y", "--unused"], dry_run=args.dry_run, check=False)

    exec_actions(actions, dry_run=args.dry_run)
    print_final_summary(False, total_bytes, unknown, total_items, categories, log_path)

def apply_default_clean_flags(args: argparse.Namespace, mode: str) -> None:
    docker_none = not any([args.containers, args.networks, args.volumes, args.builder, args.system_prune, args.truncate_logs_mb]) and args.images == "off"
    system_none = not any([args.journal, args.tmpfiles, args.apt, args.logs, args.pip_cache, args.npm_cache, args.cargo_cache, args.go_cache, args.snap, args.flatpak, args.logrotate])
    if mode in ("all", "docker") and docker_none:
        args.containers = True
        args.networks = True
        args.images = "dangling"
        args.builder = True
    if mode in ("all", "system") and system_none:
        args.journal = True
        args.tmpfiles = True
        args.apt = True
        args.logs = True
        args.kernels = False
        args.pip_cache = True
        args.npm_cache = True
        args.cargo_cache = True
        args.go_cache = True
        args.snap = True
        args.flatpak = True

def cmd_clean_all(args: argparse.Namespace) -> None:
    apply_default_clean_flags(args, "all")
    line_do("Full clean: system + docker")
    cmd_clean_system(args)
    cmd_docker_clean(args)

# -----------------------------
# TUI for analyze command
# -----------------------------
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
                    yield Static("[dim]Use arrow keys to navigate\nPress Enter to expand\nPress Q to quit[/dim]", id="help_text")
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
    target = os.path.expanduser(args.path)

    # Launch TUI if requested
    if hasattr(args, 'tui') and args.tui:
        if not TEXTUAL:
            # Offer to install textual
            p("")
            line_warn("Textual library is not installed.")
            p("Textual is required for the interactive TUI interface.")
            p("")

            if confirm("Would you like to install textual and its dependencies?", False):
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

def cmd_purge(args: argparse.Namespace) -> None:
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

def cmd_installer(args: argparse.Namespace) -> None:
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

# -----------------------------
# Uninstall app command
# -----------------------------
def is_apt_package(name: str) -> bool:
    """Check if package is installed via APT."""
    try:
        result = capture(["dpkg", "-l", name])
        # dpkg -l returns lines with package status
        # Line starting with "ii" means installed
        for line in result.split("\n"):
            if line.startswith("ii") and name in line:
                logger.debug(f"Package {name} found via APT")
                return True
        return False
    except subprocess.CalledProcessError:
        return False
    except Exception as e:
        logger.debug(f"Error checking APT package {name}: {e}")
        return False

def is_snap_package(name: str) -> bool:
    """Check if package is installed via Snap."""
    if not which("snap"):
        return False
    try:
        result = capture(["snap", "list"])
        # Check if package name appears in snap list output
        if name in result:
            logger.debug(f"Package {name} found via Snap")
            return True
        return False
    except subprocess.CalledProcessError:
        return False
    except Exception as e:
        logger.debug(f"Error checking Snap package {name}: {e}")
        return False

def is_flatpak_package(name: str) -> bool:
    """Check if package is installed via Flatpak."""
    if not which("flatpak"):
        return False
    try:
        result = capture(["flatpak", "list", "--app"])
        # Flatpak IDs usually contain dots (e.g., org.mozilla.firefox)
        # Check both exact match and partial match
        if name in result:
            logger.debug(f"Package {name} found via Flatpak")
            return True
        return False
    except subprocess.CalledProcessError:
        return False
    except Exception as e:
        logger.debug(f"Error checking Flatpak package {name}: {e}")
        return False

def get_package_config_paths(package: str) -> List[str]:
    """Get common config paths for a package."""
    home = Path.home()
    paths = [
        str(home / ".config" / package),
        str(home / ".local" / "share" / package),
        str(home / ".cache" / package),
    ]
    # Only return paths that exist
    return [p for p in paths if Path(p).exists()]

def cmd_uninstall_app(args: argparse.Namespace) -> None:
    """Uninstall applications with all associated files."""
    section("Uninstall Application")

    # Handle special flags
    if args.list_orphans:
        if not which("apt"):
            line_warn("APT not available. --list-orphans requires APT.")
            return
        p("Searching for orphaned packages...")
        try:
            result = capture(["apt-mark", "showauto"])
            orphans = result.strip().split("\n") if result.strip() else []
            if orphans:
                table("Orphaned Packages", ["Package"], [[pkg] for pkg in orphans[:50]])
                p(f"\nTotal: {len(orphans)} packages")
                p("\nTo remove: apt autoremove")
            else:
                line_ok("No orphaned packages found")
        except Exception as e:
            line_warn(f"Failed to list orphaned packages: {e}")
        return

    if args.autoremove:
        if not which("apt"):
            line_warn("APT not available. --autoremove requires APT.")
            return
        if not is_root():
            maybe_reexec_with_sudo("Root permissions required for apt autoremove.")
        p("Running apt autoremove...")
        run(["apt", "autoremove", "-y"], dry_run=args.dry_run, check=False)
        line_ok("Autoremove completed")
        return

    if args.broken:
        if not which("apt"):
            line_warn("APT not available. --broken requires APT.")
            return
        if not is_root():
            maybe_reexec_with_sudo("Root permissions required to fix broken packages.")
        p("Fixing broken packages...")
        run(["apt", "--fix-broken", "install", "-y"], dry_run=args.dry_run, check=False)
        line_ok("Fix completed")
        return

    # Require package name
    if not args.package:
        line_warn("Package name required. Usage: lm uninstall <package>")
        p("\nAvailable flags:")
        p("  --list-orphans    List orphaned packages")
        p("  --autoremove      Run apt autoremove")
        p("  --broken          Fix broken packages")
        return

    package = args.package
    logger.info(f"Attempting to uninstall package: {package}")

    # Detect package manager
    actions = []
    pkg_manager = None

    if is_apt_package(package):
        pkg_manager = "APT"
        p(f"Package '{package}' found via APT")

        # Determine apt command based on --purge flag
        if args.purge:
            actions.append(Action(f"Remove package with configs", ["apt", "remove", "--purge", "-y", package], root=True))
        else:
            actions.append(Action(f"Remove package", ["apt", "remove", "-y", package], root=True))

        # Clean up user config paths if --purge
        if args.purge:
            config_paths = get_package_config_paths(package)
            if config_paths:
                for path in config_paths:
                    actions.append(Action(f"Remove user config", ["rm", "-rf", path], root=False))

        # Autoremove after uninstall
        actions.append(Action(f"Clean up dependencies", ["apt", "autoremove", "-y"], root=True))

    elif is_snap_package(package):
        pkg_manager = "Snap"
        p(f"Package '{package}' found via Snap")

        actions.append(Action(f"Remove snap", ["snap", "remove", package], root=True))

        # Snap data is in ~/snap/<package>
        snap_data = str(Path.home() / "snap" / package)
        if Path(snap_data).exists() and args.purge:
            actions.append(Action(f"Remove snap data", ["rm", "-rf", snap_data], root=False))

    elif is_flatpak_package(package):
        pkg_manager = "Flatpak"
        p(f"Package '{package}' found via Flatpak")

        actions.append(Action(f"Remove flatpak", ["flatpak", "uninstall", "-y", package], root=False))

        # Flatpak data is in ~/.var/app/<package>
        flatpak_data = str(Path.home() / ".var" / "app" / package)
        if Path(flatpak_data).exists() and args.purge:
            actions.append(Action(f"Remove flatpak data", ["rm", "-rf", flatpak_data], root=False))

    else:
        line_warn(f"Package '{package}' not found via APT, Snap, or Flatpak")
        p("\nTip: Make sure the package name is correct:")
        p("  - APT:     use package name (e.g., 'firefox', 'vim')")
        p("  - Snap:    use snap name (e.g., 'firefox', 'spotify')")
        p("  - Flatpak: use app ID (e.g., 'org.mozilla.firefox')")
        return

    if not actions:
        line_warn("No actions to perform")
        return

    # Check whitelist
    ensure_config_files()
    whitelist = load_whitelist()

    # Filter actions based on whitelist
    # Note: for uninstall, we check if the package name is whitelisted
    if is_whitelisted(f"/uninstall/{package}", whitelist):
        line_warn(f"Package '{package}' is whitelisted and cannot be uninstalled")
        p(f"Edit whitelist: lm whitelist --edit")
        return

    # Show plan
    p("")
    show_plan(actions, f"Uninstall Plan ({pkg_manager})")
    p("")

    # Confirm and execute
    if not confirm(f"Uninstall '{package}'?", args.yes):
        p("Cancelled.")
        return

    # Check root permissions if needed
    needs_root = any(a.root for a in actions)
    if needs_root and not is_root():
        maybe_reexec_with_sudo(f"Root permissions required to uninstall {package}.")

    # Execute actions
    exec_actions(actions, dry_run=args.dry_run)

    p("")
    line_ok(f"Package '{package}' uninstalled successfully")

# -----------------------------
# Optimize system command
# -----------------------------
def cmd_optimize(args: argparse.Namespace) -> None:
    """Optimize system by rebuilding databases and restarting services."""
    section("System Optimization")

    actions = []

    # Determine what to optimize
    optimize_all = args.all or not (args.database or args.network or args.services or args.clear_cache)

    # 1. Database optimization
    if optimize_all or args.database:
        logger.info("Adding database optimization tasks")

        # updatedb - locate database
        if which("updatedb"):
            actions.append(Action("Rebuild locate database", ["updatedb"], root=True))

        # mandb - manual pages database
        if which("mandb"):
            actions.append(Action("Update man pages database", ["mandb"], root=True))

        # ldconfig - dynamic linker cache
        if which("ldconfig"):
            actions.append(Action("Rebuild dynamic linker cache", ["ldconfig"], root=True))

        # fc-cache - font cache
        if which("fc-cache"):
            actions.append(Action("Refresh font cache", ["fc-cache", "-fv"], root=False))

        # update-mime-database
        if which("update-mime-database"):
            actions.append(Action("Update MIME database",
                                 ["update-mime-database", "/usr/share/mime"], root=True))

        # update-desktop-database
        if which("update-desktop-database"):
            actions.append(Action("Update desktop database",
                                 ["update-desktop-database"], root=True))

    # 2. Network optimization
    if optimize_all or args.network:
        logger.info("Adding network optimization tasks")

        # Flush DNS cache (systemd-resolved)
        if which("systemd-resolve") or which("resolvectl"):
            # Use resolvectl on newer systems, fallback to systemd-resolve
            cmd = "resolvectl" if which("resolvectl") else "systemd-resolve"
            actions.append(Action("Flush DNS cache", [cmd, "flush-caches"], root=True))

        # Restart NetworkManager
        if which("systemctl"):
            # Check if NetworkManager is active before restarting
            try:
                result = capture(["systemctl", "is-active", "NetworkManager"])
                if "active" in result:
                    actions.append(Action("Restart NetworkManager",
                                        ["systemctl", "restart", "NetworkManager"], root=True))
            except Exception:
                pass

        # Clear ARP cache
        if which("ip"):
            actions.append(Action("Clear ARP cache",
                                 ["ip", "-s", "-s", "neigh", "flush", "all"], root=True))

    # 3. Services optimization
    if optimize_all or args.services:
        logger.info("Adding services optimization tasks")

        if which("systemctl"):
            # Reload systemd daemon
            actions.append(Action("Reload systemd daemon",
                                ["systemctl", "daemon-reload"], root=True))

            # Reset failed units
            actions.append(Action("Reset failed systemd units",
                                ["systemctl", "reset-failed"], root=True))

    # 4. Memory cache clearing (DANGEROUS - requires explicit flag)
    if args.clear_cache:
        logger.warning("Clear cache flag enabled - this can cause temporary performance degradation")
        p("")
        line_warn("⚠️  Clearing page cache can cause temporary system slowdown!")
        line_warn("⚠️  This will drop clean caches and may impact running applications.")
        p("")

        if confirm("Are you SURE you want to clear page cache?", False):
            # sync + drop caches
            actions.append(Action("Sync filesystems", ["sync"], root=True))
            actions.append(Action("Clear page cache",
                                ["sh", "-c", "echo 3 > /proc/sys/vm/drop_caches"], root=True))
        else:
            p("Cache clearing cancelled.")

    # Check if there are any actions to perform
    if not actions:
        line_warn("No optimization tasks selected or available.")
        p("\nUse flags to specify what to optimize:")
        p("  --all          All optimizations (default)")
        p("  --database     Rebuild system databases")
        p("  --network      Optimize network (DNS, NetworkManager, ARP)")
        p("  --services     Optimize systemd services")
        p("  --clear-cache  Clear page cache (DANGEROUS)")
        return

    # Show plan
    p("")
    show_plan(actions, "Optimization Plan")
    p("")

    # Confirm and execute
    if not confirm("Proceed with optimization?", args.yes):
        p("Cancelled.")
        return

    # Check root permissions if needed
    needs_root = any(a.root for a in actions)
    if needs_root and not is_root():
        maybe_reexec_with_sudo("Root permissions required for system optimization.")

    # Execute actions
    exec_actions(actions, dry_run=args.dry_run)

    p("")
    line_ok("System optimization completed")

# -----------------------------
# Whitelist management command
# -----------------------------
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

# -----------------------------
# Config command
# -----------------------------
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

# -----------------------------
# Simple interactive menu
# -----------------------------
def prompt_bool(msg: str, default: bool = False) -> bool:
    suffix = "Y/n" if default else "y/N"
    ans = input(f"{msg} [{suffix}]: ").strip().lower()
    if not ans:
        return default
    return ans in ("y", "yes")

def prompt_choice(msg: str, choices: List[str], default: str) -> str:
    raw = input(f"{msg} ({'/'.join(choices)}) [{default}]: ").strip().lower()
    if not raw:
        return default
    return raw if raw in choices else default

def prompt_int(msg: str) -> Optional[int]:
    raw = input(f"{msg} (leave empty to skip): ").strip()
    if not raw:
        return None
    try:
        return int(raw)
    except ValueError:
        return None

def simple_docker_clean() -> None:
    containers = prompt_bool("Remove stopped containers", False)
    networks = prompt_bool("Remove dangling networks", False)
    volumes = prompt_bool("Remove dangling volumes", False)
    builder = prompt_bool("Clean builder cache", False)
    builder_all = prompt_bool("Builder prune --all", False) if builder else False
    images = prompt_choice("Image cleanup", ["off", "dangling", "unused", "all"], "off")
    system_prune = prompt_bool("Run docker system prune", False)
    system_prune_all = prompt_bool("System prune -a", False) if system_prune else False
    system_prune_volumes = prompt_bool("System prune --volumes", False) if system_prune else False
    truncate_logs_mb = prompt_int("Truncate json-file logs >= N MB")
    dry_run = prompt_bool("Dry-run", True)
    assume_yes = prompt_bool("Assume confirmations (--yes)", False)

    if truncate_logs_mb is not None and not is_root() and docker_logs_dir_exists() and not can_read_docker_logs():
        maybe_reexec_with_sudo("Permissions are required to truncate Docker logs.")

    args = argparse.Namespace(
        containers=containers,
        networks=networks,
        volumes=volumes,
        builder=builder,
        builder_all=builder_all,
        images=images,
        system_prune=system_prune,
        system_prune_all=system_prune_all,
        system_prune_volumes=system_prune_volumes,
        truncate_logs_mb=truncate_logs_mb,
        dry_run=dry_run,
        yes=assume_yes,
    )
    cmd_docker_clean(args)

def simple_clean_system() -> None:
    journal = prompt_bool("Clean journald", False)
    journal_time = "14d"
    journal_size = "500M"
    if journal:
        jt = input("Retention by time (e.g. 7d, 14d, 1month) [14d]: ").strip()
        js = input("Size cap (e.g. 200M, 1G) [500M]: ").strip()
        journal_time = jt or journal_time
        journal_size = js or journal_size
    tmpfiles = prompt_bool("systemd-tmpfiles --clean", False)
    apt = prompt_bool("apt autoremove/autoclean/clean", False)
    dry_run = prompt_bool("Dry-run", True)
    assume_yes = prompt_bool("Assume confirmations (--yes)", False)

    if (journal or tmpfiles or apt) and not is_root():
        maybe_reexec_with_sudo("Root permissions are required for clean system.")

    args = argparse.Namespace(
        journal=journal,
        journal_time=journal_time,
        journal_size=journal_size,
        tmpfiles=tmpfiles,
        apt=apt,
        dry_run=dry_run,
        yes=assume_yes,
    )
    cmd_clean_system(args)

def interactive_simple() -> None:
    while True:
        clear_screen()
        print_header()
        print_banner()
        p("MAIN MENU")
        p("  1) status (all)")
        p("  2) status docker")
        p("  3) clean docker")
        p("  4) clean system")
        p("  0) exit")
        choice = input("Select an option: ").strip()
        if choice == "1":
            clear_screen()
            print_header()
            args = argparse.Namespace()
            cmd_status_all(args)
            pause()
        elif choice == "2":
            clear_screen()
            print_header()
            if not is_root() and docker_logs_dir_exists() and not can_read_docker_logs():
                maybe_reexec_with_sudo("Permissions are required to read Docker logs.")
            args = argparse.Namespace(top_logs=20)
            cmd_docker_status(args)
            pause()
        elif choice == "3":
            clear_screen()
            print_header()
            simple_docker_clean()
            pause()
        elif choice == "4":
            clear_screen()
            print_header()
            simple_clean_system()
            pause()
        elif choice == "0":
            break
        else:
            p("Invalid option.")

# -----------------------------
# Main CLI
# -----------------------------
def main() -> None:
    if len(sys.argv) == 1:
        clear_screen()
        interactive_simple()
        return
    if len(sys.argv) == 2 and sys.argv[1] in ("-h", "--help"):
        clear_screen()
        print_help()
        return
    if len(sys.argv) == 2 and sys.argv[1] in ("-V", "--version"):
        print(f"LinuxMole {VERSION}")
        return

    ap = argparse.ArgumentParser(
        prog="lm",
        description="LinuxMole: safe maintenance for Ubuntu + Docker with structured output.",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    ap.add_argument("--dry-run", action="store_true", help="Preview only, no actions executed (clean only).")
    ap.add_argument("--yes", action="store_true", help="Assume 'yes' for confirmations (clean only).")
    ap.add_argument("-v", "--verbose", action="store_true", help="Enable verbose logging (DEBUG level).")
    ap.add_argument("--log-file", type=str, metavar="PATH", help="Write logs to specified file.")

    sp = ap.add_subparsers(dest="cmd")

    sp_status = sp.add_parser("status", help="System and/or Docker status.")
    sp_status.add_argument("--top-logs", type=int, default=20, help="Number of container logs to show by size.")
    sp_status.add_argument("--paths", action="store_true", help="Analyze PATH entries and rc files.")
    sp_status_sub = sp_status.add_subparsers(dest="status_target")
    sp_status_sub.add_parser("system", help="System status only.")
    sp_status_docker = sp_status_sub.add_parser("docker", help="Docker status only.")
    sp_status_docker.add_argument("--top-logs", type=int, default=20, help="Number of container logs to show by size.")

    sp_clean = sp.add_parser("clean", help="Full cleanup or specific target (system/docker).")
    sp_clean_sub = sp_clean.add_subparsers(dest="clean_target")
    sp_clean.add_argument("--dry-run", action="store_true", help="Preview only, no actions executed.")
    sp_clean.add_argument("--yes", action="store_true", help="Assume 'yes' for confirmations.")

    def add_docker_flags(p):
        p.add_argument("--containers", action="store_true", help="Remove stopped containers (container prune).")
        p.add_argument("--networks", action="store_true", help="Remove dangling networks (network prune).")
        p.add_argument("--volumes", action="store_true", help="Remove dangling volumes (volume prune).")
        p.add_argument("--builder", action="store_true", help="Clean builder cache (builder prune).")
        p.add_argument("--builder-all", action="store_true", help="In builder prune, include all (--all).")
        p.add_argument("--images", choices=["off", "dangling", "unused", "all"], default="off",
                       help="Image cleanup: dangling (only <none>), unused/all (prune -a).")
        p.add_argument("--system-prune", action="store_true", help="Run docker system prune (controlled by flags).")
        p.add_argument("--system-prune-all", action="store_true", help="Add -a to system prune.")
        p.add_argument("--system-prune-volumes", action="store_true", help="Add --volumes to system prune (more destructive).")
        p.add_argument("--truncate-logs-mb", type=int, default=None,
                       help="Truncate json-file logs >= N MB (optional; understand impact).")

    def add_system_flags(p):
        p.add_argument("--journal", action="store_true", help="Apply journald cleanup.")
        p.add_argument("--journal-time", default="14d", help="Retention by time (e.g. 7d, 14d, 1month).")
        p.add_argument("--journal-size", default="500M", help="Size cap (e.g. 200M, 1G).")
        p.add_argument("--tmpfiles", action="store_true", help="systemd-tmpfiles --clean.")
        p.add_argument("--apt", action="store_true", help="apt autoremove/autoclean/clean.")
        p.add_argument("--logs", action="store_true", help="Clean rotated logs in /var/log.")
        p.add_argument("--logs-days", type=int, default=7, help="Log age threshold in days.")
        p.add_argument("--kernels", action="store_true", help="Remove old kernels (not default).")
        p.add_argument("--kernels-keep", type=int, default=2, help="How many kernel versions to keep.")
        p.add_argument("--pip-cache", action="store_true", help="Clean pip cache.")
        p.add_argument("--npm-cache", action="store_true", help="Clean npm cache.")
        p.add_argument("--cargo-cache", action="store_true", help="Clean cargo cache.")
        p.add_argument("--go-cache", action="store_true", help="Clean Go module cache.")
        p.add_argument("--snap", action="store_true", help="Clean old snap revisions.")
        p.add_argument("--flatpak", action="store_true", help="Clean unused flatpak runtimes.")
        p.add_argument("--logrotate", action="store_true", help="Force logrotate.")

    add_docker_flags(sp_clean)
    add_system_flags(sp_clean)
    sp_clean_system = sp_clean_sub.add_parser("system", help="System cleanup only.")
    sp_clean_docker = sp_clean_sub.add_parser("docker", help="Docker cleanup only.")
    sp_clean_system.add_argument("--dry-run", action="store_true", help="Preview only, no actions executed.")
    sp_clean_system.add_argument("--yes", action="store_true", help="Assume 'yes' for confirmations.")
    sp_clean_docker.add_argument("--dry-run", action="store_true", help="Preview only, no actions executed.")
    sp_clean_docker.add_argument("--yes", action="store_true", help="Assume 'yes' for confirmations.")
    add_system_flags(sp_clean_system)
    add_docker_flags(sp_clean_docker)

    # Uninstall app command (new)
    sp_uninstall = sp.add_parser("uninstall", help="Uninstall apps with all configs (APT/Snap/Flatpak).")
    sp_uninstall.add_argument("package", nargs="?", help="Package name to uninstall.")
    sp_uninstall.add_argument("--purge", action="store_true", help="Remove configs and user data.")
    sp_uninstall.add_argument("--list-orphans", action="store_true", help="List orphaned packages (APT).")
    sp_uninstall.add_argument("--autoremove", action="store_true", help="Run apt autoremove.")
    sp_uninstall.add_argument("--broken", action="store_true", help="Fix broken packages (APT).")
    sp_uninstall.add_argument("--dry-run", action="store_true", help="Preview only, no actions executed.")
    sp_uninstall.add_argument("--yes", action="store_true", help="Assume 'yes' for confirmations.")

    # Self-uninstall LinuxMole (renamed from old "uninstall")
    sp_self_uninstall = sp.add_parser("self-uninstall", help="Remove LinuxMole from this system.")

    # Optimize system command
    sp_optimize = sp.add_parser("optimize", help="Optimize system (rebuild DBs, flush caches, restart services).")
    sp_optimize.add_argument("--all", action="store_true", help="All optimizations (default).")
    sp_optimize.add_argument("--database", action="store_true", help="Rebuild system databases (locate, man, ldconfig, fonts, MIME).")
    sp_optimize.add_argument("--network", action="store_true", help="Network optimization (flush DNS, restart NetworkManager, clear ARP).")
    sp_optimize.add_argument("--services", action="store_true", help="Optimize systemd services (daemon-reload, reset failed units).")
    sp_optimize.add_argument("--clear-cache", action="store_true", help="Clear page cache (DANGEROUS - can cause slowdown).")
    sp_optimize.add_argument("--dry-run", action="store_true", help="Preview only, no actions executed.")
    sp_optimize.add_argument("--yes", action="store_true", help="Assume 'yes' for confirmations.")

    sp_analyze = sp.add_parser("analyze", help="Analyze disk usage.")
    sp_analyze.add_argument("--path", default=".", help="Path to analyze.")
    sp_analyze.add_argument("--top", type=int, default=10, help="Number of entries to show.")
    sp_analyze.add_argument("--tui", action="store_true", help="Launch interactive TUI (requires textual).")

    sp_purge = sp.add_parser("purge", help="Clean project build artifacts.")
    sp_purge.add_argument("--paths", action="store_true", help="Show or edit purge paths.")
    sp_purge.add_argument("--yes", action="store_true", help="Assume 'yes' for confirmations.")

    sp_installer = sp.add_parser("installer", help="Find and remove installer files.")
    sp_installer.add_argument("--yes", action="store_true", help="Assume 'yes' for confirmations.")

    # Whitelist management
    sp_whitelist = sp.add_parser("whitelist", help="Manage whitelist of protected paths.")
    sp_whitelist.add_argument("--add", type=str, metavar="PATTERN", help="Add glob pattern to whitelist.")
    sp_whitelist.add_argument("--remove", type=str, metavar="PATTERN", help="Remove glob pattern from whitelist.")
    sp_whitelist.add_argument("--test", type=str, metavar="PATH", help="Test if path is protected.")
    sp_whitelist.add_argument("--edit", action="store_true", help="Open whitelist in $EDITOR.")

    # Configuration management
    sp_config = sp.add_parser("config", help="Manage configuration file.")
    sp_config.add_argument("--edit", action="store_true", help="Open config in $EDITOR.")
    sp_config.add_argument("--reset", action="store_true", help="Reset to default configuration.")

    sp_update = sp.add_parser("update", help="Update LinuxMole (pipx).")

    args = ap.parse_args()

    # Setup logging
    setup_logging(
        verbose=getattr(args, 'verbose', False),
        log_file=getattr(args, 'log_file', None)
    )
    logger.debug(f"Command invoked: {' '.join(sys.argv)}")

    if args.cmd is None:
        print_help()
        return
    clear_screen()
    print_header()
    if args.cmd not in ("clean", "uninstall", "optimize") and (args.dry_run or args.yes):
        line_warn("--dry-run and --yes apply to clean, uninstall, and optimize only.")
        return
    if args.cmd == "status":
        target = args.status_target or "all"
        if target == "system":
            cmd_status_system(args)
        elif target == "docker":
            cmd_docker_status(args)
        else:
            cmd_status_all(args)
    elif args.cmd == "clean":
        target = args.clean_target or "all"
        if target == "system":
            cmd_clean_system(args)
        elif target == "docker":
            cmd_docker_clean(args)
        else:
            cmd_clean_all(args)
    elif args.cmd == "uninstall":
        cmd_uninstall_app(args)
    elif args.cmd == "self-uninstall":
        if not is_root():
            maybe_reexec_with_sudo("Root permissions are required to uninstall LinuxMole.")
        if not confirm("Uninstall LinuxMole?", False):
            p("Cancelled.")
            return
        run(["rm", "-rf", "/opt/linuxmole"], dry_run=False, check=False)
        run(["rm", "-f", "/usr/local/bin/lm"], dry_run=False, check=False)
        p("LinuxMole removed.")
    elif args.cmd == "optimize":
        cmd_optimize(args)
    elif args.cmd == "analyze":
        cmd_analyze(args)
    elif args.cmd == "purge":
        cmd_purge(args)
    elif args.cmd == "installer":
        cmd_installer(args)
    elif args.cmd == "whitelist":
        cmd_whitelist(args)
    elif args.cmd == "config":
        cmd_config(args)
    elif args.cmd == "update":
        if not which("pipx"):
            line_warn("pipx not found. Install pipx to use update.")
            return
        run(["pipx", "upgrade", "linuxmole"], dry_run=False, check=False)
    else:
        interactive_simple()

if __name__ == "__main__":
    main()
