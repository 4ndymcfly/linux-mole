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


def simple_docker_clean() -> None:
    """Interactive Docker cleanup wizard."""
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

    if (truncate_logs_mb is not None and not is_root() and
        docker_logs_dir_exists() and not can_read_docker_logs()):
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
    """Interactive system cleanup wizard."""
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
            args = argparse.Namespace(paths=False)
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
