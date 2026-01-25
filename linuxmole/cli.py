#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CLI entry point and argument parser for LinuxMole.
"""

from __future__ import annotations
import sys
import argparse
from typing import List, Tuple, Optional

from linuxmole.constants import VERSION, RICH, console
from linuxmole.logging_setup import setup_logging, logger
from linuxmole.output import print_banner, print_header, p, line_warn
from linuxmole.helpers import clear_screen, which, is_root, run, maybe_reexec_with_sudo, confirm
from linuxmole.interactive import interactive_simple
from linuxmole.commands import (
    cmd_status_system,
    cmd_status_all,
    cmd_docker_status,
    cmd_clean_all,
    cmd_clean_system,
    cmd_docker_clean,
    cmd_uninstall_app,
    cmd_optimize,
    cmd_analyze,
    cmd_purge,
    cmd_installer,
    cmd_whitelist,
    cmd_config,
)


def print_help() -> None:
    """Print custom help message."""
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


def main() -> None:
    """Main CLI entry point."""
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

    # Status command
    sp_status = sp.add_parser("status", help="System and/or Docker status.")
    sp_status.add_argument("--top-logs", type=int, default=20, help="Number of container logs to show by size.")
    sp_status.add_argument("--paths", action="store_true", help="Analyze PATH entries and rc files.")
    sp_status_sub = sp_status.add_subparsers(dest="status_target")
    sp_status_sub.add_parser("system", help="System status only.")
    sp_status_docker = sp_status_sub.add_parser("docker", help="Docker status only.")
    sp_status_docker.add_argument("--top-logs", type=int, default=20, help="Number of container logs to show by size.")

    # Clean command
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
        p.add_argument("--journal-time", default=None, help="Retention by time (e.g. 7d, 14d, 1month). Default from config.")
        p.add_argument("--journal-size", default=None, help="Size cap (e.g. 200M, 1G). Default from config.")
        p.add_argument("--tmpfiles", action="store_true", help="systemd-tmpfiles --clean.")
        p.add_argument("--apt", action="store_true", help="apt autoremove/autoclean/clean.")
        p.add_argument("--logs", action="store_true", help="Clean rotated logs in /var/log.")
        p.add_argument("--logs-days", type=int, default=None, help="Log age threshold in days. Default from config.")
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

    # Uninstall app command
    sp_uninstall = sp.add_parser("uninstall", help="Uninstall apps with all configs (APT/Snap/Flatpak).")
    sp_uninstall.add_argument("package", nargs="?", help="Package name to uninstall.")
    sp_uninstall.add_argument("--purge", action="store_true", help="Remove configs and user data.")
    sp_uninstall.add_argument("--list-orphans", action="store_true", help="List orphaned packages (APT).")
    sp_uninstall.add_argument("--autoremove", action="store_true", help="Run apt autoremove.")
    sp_uninstall.add_argument("--broken", action="store_true", help="Fix broken packages (APT).")
    sp_uninstall.add_argument("--dry-run", action="store_true", help="Preview only, no actions executed.")
    sp_uninstall.add_argument("--yes", action="store_true", help="Assume 'yes' for confirmations.")

    # Self-uninstall LinuxMole
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

    # Analyze command
    sp_analyze = sp.add_parser("analyze", help="Analyze disk usage.")
    sp_analyze.add_argument("--path", default=".", help="Path to analyze.")
    sp_analyze.add_argument("--top", type=int, default=10, help="Number of entries to show.")
    sp_analyze.add_argument("--tui", action="store_true", help="Launch interactive TUI (requires textual).")

    # Purge command
    sp_purge = sp.add_parser("purge", help="Clean project build artifacts.")
    sp_purge.add_argument("--paths", action="store_true", help="Show or edit purge paths.")
    sp_purge.add_argument("--yes", action="store_true", help="Assume 'yes' for confirmations.")

    # Installer command
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

    # Update command
    sp_update = sp.add_parser("update", help="Update LinuxMole (pipx).")

    # Parse arguments
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

    if args.cmd not in ("clean", "uninstall", "optimize") and (
        getattr(args, 'dry_run', False) or getattr(args, 'yes', False)
    ):
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


if __name__ == "__main__":
    main()
