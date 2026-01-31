#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Interactive menu functions for LinuxMole.
Enhanced with complete command coverage and improved UX.
"""

from __future__ import annotations
import argparse
import sys
from typing import List, Optional

from linuxmole.output import p, print_header, print_banner
from linuxmole.helpers import (
    clear_screen, pause, is_root, maybe_reexec_with_sudo, which, run
)
from linuxmole.docker.logs import docker_logs_dir_exists, can_read_docker_logs
from linuxmole.constants import VERSION
from linuxmole.commands import (
    cmd_status_all, cmd_status_system, cmd_docker_status,
    cmd_docker_clean, cmd_clean_system,
    cmd_analyze, cmd_purge, cmd_installer,
    cmd_uninstall_app, cmd_optimize,
    cmd_whitelist, cmd_config
)


def prompt_bool(msg: str, default: bool = False) -> bool:
    """Prompt user for a boolean choice."""
    suffix = "Y/n" if default else "y/N"
    ans = input(f"{msg} [{suffix}]: ").strip().lower()
    if not ans:
        return default
    return ans in ("y", "yes")


def prompt_choice(msg: str, choices: List[str], default: str) -> str:
    """Prompt user to choose from a list of options."""
    raw = input(f"{msg} ({'/'.join(choices)}) [{default}]: ").strip().lower()
    if not raw:
        return default
    return raw if raw in choices else default


def prompt_int(msg: str) -> Optional[int]:
    """Prompt user for an integer value."""
    raw = input(f"{msg} (leave empty to skip): ").strip()
    if not raw:
        return None
    try:
        return int(raw)
    except ValueError:
        return None


# ══════════════════════════════════════════════════════════════
# UI Helper Functions - Enhanced for FASE 1
# ══════════════════════════════════════════════════════════════

def print_category_header(icon: str, title: str) -> None:
    """Print a category header with icon."""
    p("")
    p(f"{icon} {title}")


def print_separator(char: str = "═", length: int = 65) -> None:
    """Print a visual separator."""
    p(char * length)


def print_status_indicators(dry_run_mode: bool) -> None:
    """Print current mode indicators."""
    indicators = []

    if dry_run_mode:
        indicators.append("🔍 DRY-RUN MODE")
    else:
        indicators.append("✓ NORMAL MODE")

    if is_root():
        indicators.append("⚠️  ROOT MODE")

    if indicators:
        p("  ".join(indicators))
        p("")


def simple_docker_clean(dry_run_mode: bool = False) -> None:
    """Interactive Docker cleanup wizard."""
    # Changed defaults to True (Y/n instead of y/N)
    containers = prompt_bool("Remove stopped containers", True)
    networks = prompt_bool("Remove dangling networks", True)
    volumes = prompt_bool("Remove dangling volumes", True)
    builder = prompt_bool("Clean builder cache", True)
    builder_all = prompt_bool("Builder prune --all", True) if builder else False
    images = prompt_choice("Image cleanup", ["off", "dangling", "unused", "all"], "dangling")
    system_prune = prompt_bool("Run docker system prune", True)
    system_prune_all = prompt_bool("System prune -a", True) if system_prune else False
    system_prune_volumes = prompt_bool("System prune --volumes", True) if system_prune else False
    truncate_logs_mb = prompt_int("Truncate json-file logs >= N MB")

    # Don't ask for dry-run if already in dry-run mode
    dry_run = dry_run_mode if dry_run_mode else prompt_bool("Dry-run", True)
    assume_yes = prompt_bool("Assume confirmations (--yes)", True)

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


def simple_clean_system(dry_run_mode: bool = False) -> None:
    """Interactive system cleanup wizard."""
    # Changed defaults to True (Y/n instead of y/N)
    journal = prompt_bool("Clean journald", True)
    journal_time = "14d"
    journal_size = "500M"
    if journal:
        jt = input("Retention by time (e.g. 7d, 14d, 1month) [14d]: ").strip()
        js = input("Size cap (e.g. 200M, 1G) [500M]: ").strip()
        journal_time = jt or journal_time
        journal_size = js or journal_size
    tmpfiles = prompt_bool("systemd-tmpfiles --clean", True)
    apt = prompt_bool("apt autoremove/autoclean/clean", True)

    # Don't ask for dry-run if already in dry-run mode
    dry_run = dry_run_mode if dry_run_mode else prompt_bool("Dry-run", True)
    assume_yes = prompt_bool("Assume confirmations (--yes)", True)

    # Root check is now done before calling this function

    args = argparse.Namespace(
        journal=journal,
        journal_time=journal_time,
        journal_size=journal_size,
        tmpfiles=tmpfiles,
        apt=apt,
        logs=False,
        logs_days=7,
        kernels=False,
        kernels_keep=2,
        pip_cache=False,
        npm_cache=False,
        cargo_cache=False,
        go_cache=False,
        snap=False,
        flatpak=False,
        logrotate=False,
        dry_run=dry_run,
        yes=assume_yes,
    )
    cmd_clean_system(args)


# ══════════════════════════════════════════════════════════════
# Command Wizards - New (FASE 1)
# ══════════════════════════════════════════════════════════════

def simple_analyze() -> None:
    """Interactive disk analysis wizard."""
    p("=== Disk Usage Analyzer ===")
    p("")

    # Path selection
    path = input("Path to analyze [/]: ").strip() or "/"

    # Top N
    top_input = input("Number of top directories [10]: ").strip()
    top = int(top_input) if top_input.isdigit() else 10

    # TUI mode
    use_tui = prompt_bool("Use interactive TUI (recommended)", True)

    args = argparse.Namespace(
        path=path,
        top=top,
        tui=use_tui
    )
    cmd_analyze(args)


def simple_purge() -> None:
    """Interactive purge build artifacts wizard."""
    p("=== Purge Build Artifacts ===")
    p("")
    p("This will search and remove common build artifacts:")
    p("  • node_modules/")
    p("  • target/ (Rust)")
    p("  • build/, dist/")
    p("  • __pycache__/, *.pyc")
    p("  • .venv/, venv/")
    p("")
    p("Searches in paths from: ~/.config/linuxmole/purge_paths.txt")
    p("")

    # Ask for confirmation preference
    auto_yes = not prompt_bool("Ask for confirmation before purging", True)

    args = argparse.Namespace(
        paths=False,
        yes=auto_yes
    )
    cmd_purge(args)


def simple_installer() -> None:
    """Interactive installer files removal wizard."""
    p("=== Remove Installer Files ===")
    p("")
    p("This will find and optionally remove:")
    p("  • .deb files (Debian packages)")
    p("  • .rpm files (Red Hat packages)")
    p("  • .AppImage files")
    p("  • .iso files (disc images)")
    p("")

    # Start path
    start_path = input("Start path [~]: ").strip() or "~"

    # Dry-run
    dry_run = prompt_bool("Dry-run (preview only)", True)

    args = argparse.Namespace(
        path=start_path,
        dry_run=dry_run
    )
    cmd_installer(args)


def simple_uninstall() -> None:
    """Interactive application uninstaller wizard."""
    p("=== Uninstall Applications ===")
    p("")

    # Submenu
    p("Options:")
    p("  1) Uninstall a specific package")
    p("  2) List orphaned packages")
    p("  3) Run autoremove")
    p("  4) Fix broken packages")
    p("  0) Back")
    p("")

    choice = input("Select option: ").strip()

    if choice == "0":
        return
    elif choice == "1":
        package = input("Package name: ").strip()
        if not package:
            p("No package specified.")
            pause()
            return

        purge = prompt_bool("Remove configs and data (--purge)", True)
        dry_run = prompt_bool("Dry-run", True)

        # Root check
        if not is_root() and not dry_run:
            if not prompt_bool("Root permissions required. Execute with sudo?", True):
                pause()
                return
            maybe_reexec_with_sudo("Executing with root permissions...")

        args = argparse.Namespace(
            package=package,
            purge=purge,
            list_orphans=False,
            autoremove=False,
            broken=False,
            dry_run=dry_run
        )
        cmd_uninstall_app(args)

    elif choice == "2":
        args = argparse.Namespace(
            package=None,
            purge=False,
            list_orphans=True,
            autoremove=False,
            broken=False,
            dry_run=False
        )
        cmd_uninstall_app(args)

    elif choice == "3":
        if prompt_bool("Run apt autoremove?", True):
            # Root check
            if not is_root():
                if not prompt_bool("Root permissions required. Execute with sudo?", True):
                    pause()
                    return
                maybe_reexec_with_sudo("Executing with root permissions...")

            args = argparse.Namespace(
                package=None,
                purge=False,
                list_orphans=False,
                autoremove=True,
                broken=False,
                dry_run=False
            )
            cmd_uninstall_app(args)

    elif choice == "4":
        if prompt_bool("Attempt to fix broken packages?", True):
            # Root check
            if not is_root():
                if not prompt_bool("Root permissions required. Execute with sudo?", True):
                    pause()
                    return
                maybe_reexec_with_sudo("Executing with root permissions...")

            args = argparse.Namespace(
                package=None,
                purge=False,
                list_orphans=False,
                autoremove=False,
                broken=True,
                dry_run=False
            )
            cmd_uninstall_app(args)
    else:
        p("Invalid option.")
        pause()


def simple_optimize() -> None:
    """Interactive system optimization wizard."""
    p("=== System Optimization ===")
    p("")
    p("Select optimizations to perform:")
    p("")

    # Optimization categories
    database = prompt_bool("📚 Rebuild databases (locate, man, ldconfig, fonts)", True)
    network = prompt_bool("🌐 Network optimization (flush DNS, clear ARP)", True)
    services = prompt_bool("⚙️  Systemd services (daemon-reload, reset failed)", True)

    p("")
    p("⚠️  ADVANCED OPTION (can cause temporary slowdown):")
    clear_cache = prompt_bool("💾 Clear page cache", False)

    if not any([database, network, services, clear_cache]):
        p("No optimizations selected.")
        pause()
        return

    # Dry-run
    dry_run = prompt_bool("Dry-run (preview only)", True)

    # Root check
    if not is_root() and not dry_run:
        if not prompt_bool("Root permissions required. Execute with sudo?", True):
            pause()
            return
        maybe_reexec_with_sudo("Executing with root permissions...")

    args = argparse.Namespace(
        all=False,
        database=database,
        network=network,
        services=services,
        clear_cache=clear_cache,
        dry_run=dry_run
    )
    cmd_optimize(args)


def simple_whitelist() -> None:
    """Interactive whitelist management."""
    while True:
        clear_screen()
        print_header()

        p("=== Whitelist Management ===")
        p("")
        p("  1) Show current whitelist")
        p("  2) Add new pattern")
        p("  3) Remove pattern")
        p("  4) Test if path is protected")
        p("  5) Edit in $EDITOR")
        p("  0) Back")
        p("")

        choice = input("Select option: ").strip()

        if choice == "0":
            break
        elif choice == "1":
            args = argparse.Namespace(add=None, remove=None, test=None, edit=False)
            cmd_whitelist(args)
            pause()
        elif choice == "2":
            pattern = input("Pattern to add (e.g., /home/*/projects/*): ").strip()
            if pattern:
                args = argparse.Namespace(add=pattern, remove=None, test=None, edit=False)
                cmd_whitelist(args)
            pause()
        elif choice == "3":
            pattern = input("Pattern to remove: ").strip()
            if pattern:
                args = argparse.Namespace(add=None, remove=pattern, test=None, edit=False)
                cmd_whitelist(args)
            pause()
        elif choice == "4":
            path = input("Path to test: ").strip()
            if path:
                args = argparse.Namespace(add=None, remove=None, test=path, edit=False)
                cmd_whitelist(args)
            pause()
        elif choice == "5":
            args = argparse.Namespace(add=None, remove=None, test=None, edit=True)
            cmd_whitelist(args)
            pause()
        else:
            p("Invalid option.")
            pause()


def simple_config() -> None:
    """Interactive configuration management."""
    clear_screen()
    print_header()

    p("=== Configuration Management ===")
    p("")
    p("  1) Show current configuration")
    p("  2) Edit in $EDITOR")
    p("  3) Reset to defaults")
    p("  0) Back")
    p("")

    choice = input("Select option: ").strip()

    if choice == "0":
        return
    elif choice == "1":
        args = argparse.Namespace(show=True, edit=False, reset=False)
        cmd_config(args)
        pause()
    elif choice == "2":
        args = argparse.Namespace(show=False, edit=True, reset=False)
        cmd_config(args)
        pause()
    elif choice == "3":
        p("")
        p("⚠️  This will reset all configuration to defaults.")
        p("⚠️  A backup will be created at config.toml.bak")
        p("")
        if prompt_bool("Proceed with reset?", False):
            args = argparse.Namespace(show=False, edit=False, reset=True)
            cmd_config(args)
        pause()
    else:
        p("Invalid option.")
        pause()


def simple_update() -> None:
    """Update LinuxMole to latest version."""
    clear_screen()
    print_header()

    p("=== Update LinuxMole ===")
    p("")
    p("This will update LinuxMole to the latest version using pipx.")
    p("")
    p(f"Current version: {VERSION}")
    p("")

    if not which("pipx"):
        p("⚠️  pipx is not installed.")
        p("   Install with: sudo apt install pipx")
        pause()
        return

    if prompt_bool("Check for updates and install?", True):
        p("")
        p("Updating LinuxMole...")
        run(["pipx", "upgrade", "linuxmole"], dry_run=False)
        p("")
        p("✓ Update completed.")
        p("")
        p("Run 'lm --version' to verify the new version.")
        pause()


def simple_self_uninstall() -> None:
    """Uninstall LinuxMole from system."""
    clear_screen()
    print_header()

    p("=== Self-Uninstall LinuxMole ===")
    p("")
    p("⚠️  ⚠️  ⚠️  WARNING ⚠️  ⚠️  ⚠️")
    p("")
    p("This will COMPLETELY REMOVE LinuxMole from your system.")
    p("")
    p("What will be removed:")
    p("  • LinuxMole executable (pipx package)")
    p("")
    p("What will be PRESERVED:")
    p("  • Configuration (~/.config/linuxmole/)")
    p("  • Whitelist patterns")
    p("")

    if not prompt_bool("Are you ABSOLUTELY SURE you want to uninstall?", False):
        p("Uninstall cancelled.")
        pause()
        return

    p("")
    p("⚠️  LAST CONFIRMATION")
    if not prompt_bool("Really uninstall LinuxMole? (no going back)", False):
        p("Uninstall cancelled.")
        pause()
        return

    p("")
    p("Uninstalling LinuxMole...")

    if which("pipx"):
        run(["pipx", "uninstall", "linuxmole"], dry_run=False)
        p("")
        p("✓ LinuxMole has been removed.")
        p("✓ Configuration preserved in ~/.config/linuxmole/")
        p("")
        p("To reinstall: pipx install linuxmole")
    else:
        p("⚠️  pipx not found. Manual removal may be needed.")

    input("\nPress Enter to exit...")
    sys.exit(0)


def interactive_simple() -> None:
    """Run the simple interactive menu."""
    # First, select mode
    while True:
        clear_screen()
        print_header()
        print_banner()

        # Show ROOT MODE indicator if running as root
        root_indicator = " ⚠️  ROOT MODE" if is_root() else ""
        p("SELECT MODE" + root_indicator)

        if is_root():
            p("  ⚠️  Running as root - all operations will execute with elevated permissions")
            p("")

        p("  1) Normal Mode")
        p("  2) Dry-Run Mode")
        p("  0) Exit")
        mode_choice = input("Select an option: ").strip()

        if mode_choice == "0":
            break
        elif mode_choice not in ("1", "2"):
            p("Invalid option.")
            pause()
            continue

        # Mode selected: 1=Normal, 2=Dry-Run
        dry_run_mode = (mode_choice == "2")
        mode_suffix = " (Dry-Run Mode)" if dry_run_mode else ""

        # Main menu loop
        while True:
            clear_screen()
            print_header()
            print_banner()
            print_separator()

            p("MAIN MENU")
            print_status_indicators(dry_run_mode)

            # ── MONITORING & ANALYSIS ──
            print_category_header("📊", "MONITORING & ANALYSIS")
            p("  1) Status (System + Docker)")
            p("  2) Status System only")
            p("  3) Status Docker only")
            p("  4) Analyze Disk Usage (with TUI)")

            # ── CLEANUP & MAINTENANCE ──
            print_category_header("🧹", "CLEANUP & MAINTENANCE")
            p("  5) Clean Docker (interactive)")
            p("  6) Clean System (interactive)")
            p("  7) Purge Build Artifacts")
            p("  8) Remove Installer Files")

            # ── SYSTEM OPERATIONS ──
            print_category_header("🔧", "SYSTEM OPERATIONS")
            p("  9) Uninstall Applications")
            p(" 10) Optimize System")

            # ── CONFIGURATION ──
            print_category_header("⚙️ ", "CONFIGURATION")
            p(" 11) Manage Whitelist")
            p(" 12) Manage Configuration")

            # ── LINUXMOLE SYSTEM ──
            print_category_header("🔄", "LINUXMOLE SYSTEM")
            p(" 13) Update LinuxMole")
            p(" 14) Self-Uninstall LinuxMole")

            print_separator()
            p("  0) Back to mode selection")
            print_separator()

            choice = input("Select an option [1-14, 0]: ").strip()

            if choice == "0":
                break

            # ── MONITORING & ANALYSIS ──
            elif choice == "1":  # Status (all)
                clear_screen()
                print_header()
                if not is_root() and docker_logs_dir_exists() and not can_read_docker_logs():
                    if not prompt_bool("Root permissions recommended to read Docker logs. Execute with sudo?", True):
                        pause()
                        continue
                    maybe_reexec_with_sudo("Executing with root permissions...")
                args = argparse.Namespace(paths=False)
                cmd_status_all(args)
                pause()

            elif choice == "2":  # Status system
                clear_screen()
                print_header()
                args = argparse.Namespace(paths=False)
                cmd_status_system(args)
                pause()

            elif choice == "3":  # Status docker
                clear_screen()
                print_header()
                if not is_root() and docker_logs_dir_exists() and not can_read_docker_logs():
                    if not prompt_bool("Root permissions recommended to read Docker logs. Execute with sudo?", True):
                        pause()
                        continue
                    maybe_reexec_with_sudo("Executing with root permissions...")
                args = argparse.Namespace(top_logs=20)
                cmd_docker_status(args)
                pause()

            elif choice == "4":  # Analyze
                clear_screen()
                print_header()
                simple_analyze()
                pause()

            # ── CLEANUP & MAINTENANCE ──
            elif choice == "5":  # Clean docker
                clear_screen()
                print_header()
                if not is_root() and docker_logs_dir_exists() and not can_read_docker_logs():
                    if not prompt_bool("Root permissions recommended for log operations. Execute with sudo?", True):
                        pause()
                        continue
                    maybe_reexec_with_sudo("Executing with root permissions...")
                simple_docker_clean(dry_run_mode)
                pause()

            elif choice == "6":  # Clean system
                clear_screen()
                print_header()
                if not is_root():
                    if not prompt_bool("Root permissions are required. Execute with sudo?", True):
                        pause()
                        continue
                    maybe_reexec_with_sudo("Executing with root permissions...")
                simple_clean_system(dry_run_mode)
                pause()

            elif choice == "7":  # Purge
                clear_screen()
                print_header()
                simple_purge()
                pause()

            elif choice == "8":  # Installer
                clear_screen()
                print_header()
                simple_installer()
                pause()

            # ── SYSTEM OPERATIONS ──
            elif choice == "9":  # Uninstall
                clear_screen()
                print_header()
                simple_uninstall()
                pause()

            elif choice == "10":  # Optimize
                clear_screen()
                print_header()
                simple_optimize()
                pause()

            # ── CONFIGURATION ──
            elif choice == "11":  # Whitelist
                simple_whitelist()  # Ya tiene su propio loop

            elif choice == "12":  # Config
                simple_config()

            # ── LINUXMOLE SYSTEM ──
            elif choice == "13":  # Update
                simple_update()

            elif choice == "14":  # Self-uninstall
                simple_self_uninstall()

            else:
                p("Invalid option.")
                pause()
