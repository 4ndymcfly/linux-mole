#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Interactive menu functions for LinuxMole.
"""

from __future__ import annotations
import argparse
from typing import List, Optional

from linuxmole.output import p, print_header, print_banner
from linuxmole.helpers import clear_screen, pause, is_root, maybe_reexec_with_sudo
from linuxmole.docker.logs import docker_logs_dir_exists, can_read_docker_logs
from linuxmole.commands import cmd_status_all, cmd_docker_status, cmd_docker_clean, cmd_clean_system


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


def interactive_simple() -> None:
    """Run the simple interactive menu."""
    # First, select mode
    while True:
        clear_screen()
        print_header()
        print_banner()
        p("SELECT MODE")
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
            p("MAIN MENU" + mode_suffix)
            p(f"  1) Status (all){mode_suffix}")
            p(f"  2) Status docker{mode_suffix}")
            p(f"  3) Clean docker{mode_suffix}")
            p(f"  4) Clean system{mode_suffix}")
            p("  0) Back to mode selection")
            choice = input("Select an option: ").strip()

            if choice == "0":
                break
            elif choice == "1":
                clear_screen()
                print_header()
                # Status all: may need root for Docker logs
                if not is_root() and docker_logs_dir_exists() and not can_read_docker_logs():
                    if not prompt_bool("Root permissions recommended to read Docker logs. Execute with sudo?", True):
                        pause()
                        continue
                    maybe_reexec_with_sudo("Executing with root permissions...")
                args = argparse.Namespace(paths=False)
                cmd_status_all(args)
                pause()
            elif choice == "2":
                clear_screen()
                print_header()
                # Status docker: may need root for logs
                if not is_root() and docker_logs_dir_exists() and not can_read_docker_logs():
                    if not prompt_bool("Root permissions recommended to read Docker logs. Execute with sudo?", True):
                        pause()
                        continue
                    maybe_reexec_with_sudo("Executing with root permissions...")
                args = argparse.Namespace(top_logs=20)
                cmd_docker_status(args)
                pause()
            elif choice == "3":
                clear_screen()
                print_header()
                # Clean docker: may need root for truncating logs
                if not is_root() and docker_logs_dir_exists() and not can_read_docker_logs():
                    if not prompt_bool("Root permissions recommended for log operations. Execute with sudo?", True):
                        pause()
                        continue
                    maybe_reexec_with_sudo("Executing with root permissions...")
                simple_docker_clean(dry_run_mode)
                pause()
            elif choice == "4":
                clear_screen()
                print_header()
                # Clean system: ALWAYS requires root
                if not is_root():
                    if not prompt_bool("Root permissions are required. Execute with sudo?", True):
                        pause()
                        continue
                    maybe_reexec_with_sudo("Executing with root permissions...")
                simple_clean_system(dry_run_mode)
                pause()
            else:
                p("Invalid option.")
                pause()
