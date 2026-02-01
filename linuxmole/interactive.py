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
    """Print a modern category header with icon and styling."""
    from linuxmole.constants import RICH, console

    if RICH and console:
        console.print(f"\n  {icon} [bold cyan]{title}[/bold cyan]")
    else:
        p(f"\n  {icon} {title}")


def print_submenu_header(title: str) -> None:
    """Print modern submenu header with LinuxMole branding."""
    from linuxmole.constants import RICH, console

    clear_screen()
    print_header()

    if RICH and console:
        console.print(f"\n[bold white]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/bold white]")
        console.print(f"  [bold cyan]{title}[/bold cyan]")
        console.print(f"[bold white]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/bold white]\n")
    else:
        p("\n═══════════════════════════════════════════════════════════")
        p(f"  {title}")
        p("═══════════════════════════════════════════════════════════\n")


def print_mode_banner(dry_run_mode: bool) -> None:
    """Print modern mode indicator banner."""
    from linuxmole.constants import RICH, console

    # Dry-run mode has priority over root detection
    # (dry-run can run with root permissions but should show DRY-RUN MODE)
    if dry_run_mode:
        mode_text = "DRY-RUN MODE"
        mode_icon = "🔍"
        mode_color = "yellow"
    elif is_root():
        mode_text = "ROOT MODE"
        mode_icon = "⚠️"
        mode_color = "red"
    else:
        mode_text = "NORMAL MODE"
        mode_icon = "✓"
        mode_color = "green"

    if RICH and console:
        console.print(f"\n  [{mode_color}]■[/{mode_color}] [bold {mode_color}]{mode_text}[/bold {mode_color}]\n")
    else:
        p(f"\n  {mode_icon} {mode_text}\n")


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
    p("Searches in: ~/Downloads, ~/Desktop")
    p("")

    # Ask for confirmation preference
    auto_yes = not prompt_bool("Ask for confirmation before removing", True)

    args = argparse.Namespace(
        yes=auto_yes
    )
    cmd_installer(args)


def simple_uninstall(dry_run_mode: bool = False) -> None:
    """Interactive application uninstaller wizard."""
    from linuxmole.constants import RICH, console

    print_submenu_header("UNINSTALL APPLICATIONS")

    # Submenu options
    if RICH and console:
        console.print("  [cyan]1[/cyan]   Uninstall a specific package")
        console.print("  [cyan]2[/cyan]   List orphaned packages")
        console.print("  [cyan]3[/cyan]   Run autoremove")
        console.print("  [cyan]4[/cyan]   Fix broken packages")
        console.print("\n  [white]0[/white]   Back to main menu\n")
    else:
        p("  1   Uninstall a specific package")
        p("  2   List orphaned packages")
        p("  3   Run autoremove")
        p("  4   Fix broken packages")
        p("\n  0   Back to main menu\n")

    choice = input("  → ").strip()

    if choice == "0":
        return
    elif choice == "1":
        package = input("Package name: ").strip()
        if not package:
            p("No package specified.")
            pause()
            return

        purge = prompt_bool("Remove configs and data (--purge)", True)

        # Dry-run: only ask if not already in dry-run mode
        if dry_run_mode:
            dry_run = True  # Already in dry-run mode from main menu
        else:
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
            dry_run=dry_run,
            yes=False
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


def simple_optimize(dry_run_mode: bool = False) -> None:
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

    # Dry-run: only ask if not already in dry-run mode
    if dry_run_mode:
        dry_run = True  # Already in dry-run mode from main menu
    else:
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
        dry_run=dry_run,
        yes=False
    )
    cmd_optimize(args)


def simple_whitelist() -> None:
    """Interactive whitelist management."""
    from linuxmole.constants import RICH, console

    while True:
        print_submenu_header("WHITELIST MANAGEMENT")

        # Submenu options
        if RICH and console:
            console.print("  [cyan]1[/cyan]   Show current whitelist")
            console.print("  [cyan]2[/cyan]   Add new pattern")
            console.print("  [cyan]3[/cyan]   Remove pattern")
            console.print("  [cyan]4[/cyan]   Test if path is protected")
            console.print("  [cyan]5[/cyan]   Edit in text editor")
            console.print("\n  [white]0[/white]   Back to main menu\n")
        else:
            p("  1   Show current whitelist")
            p("  2   Add new pattern")
            p("  3   Remove pattern")
            p("  4   Test if path is protected")
            p("  5   Edit in text editor")
            p("\n  0   Back to main menu\n")

        choice = input("  → ").strip()

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
    from linuxmole.constants import RICH, console

    print_submenu_header("CONFIGURATION MANAGEMENT")

    # Submenu options
    if RICH and console:
        console.print("  [cyan]1[/cyan]   Show current configuration")
        console.print("  [cyan]2[/cyan]   Edit in text editor")
        console.print("  [cyan]3[/cyan]   Reset to defaults")
        console.print("\n  [white]0[/white]   Back to main menu\n")
    else:
        p("  1   Show current configuration")
        p("  2   Edit in text editor")
        p("  3   Reset to defaults")
        p("\n  0   Back to main menu\n")

    choice = input("  → ").strip()

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
    """Run the modern interactive menu with improved UX."""
    from linuxmole.constants import RICH, console
    import sys

    # ═══════════════════════════════════════════════════════════
    # STEP 1: Determine execution mode
    # ═══════════════════════════════════════════════════════════

    # Check if we're coming from dry-run re-execution via internal flag
    dry_run_from_args = "--interactive-dry-run" in sys.argv

    # If already running as root, check if it's dry-run mode or normal root mode
    if is_root():
        dry_run_mode = dry_run_from_args  # True if from dry-run, False if normal root
        # Go directly to main menu (skip mode selection)
    else:
        # Not root - show mode selection
        clear_screen()
        print_header()
        print_banner(banner_style="cyan", url_style="cyan")

        if RICH and console:
            console.print("\n[bold white]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/bold white]")
            console.print("  [bold cyan]SELECT EXECUTION MODE[/bold cyan]")
            console.print("[bold white]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/bold white]\n")
        else:
            p("\n═══════════════════════════════════════════════════════════")
            p("  SELECT EXECUTION MODE")
            p("═══════════════════════════════════════════════════════════\n")

        # Mode options
        if RICH and console:
            console.print("  [bold green]1[/bold green]  Normal Mode     [dim]Execute without root permissions[/dim]")
            console.print("  [bold red]2[/bold red]  Root Mode       [dim]Execute with root permissions[/dim]")
            console.print("  [bold yellow]3[/bold yellow]  Dry-Run Mode    [dim]Preview commands without executing[/dim]")
            console.print("\n  [bold white]0[/bold white]  Exit\n")
        else:
            p("  1  Normal Mode     (Execute without root permissions)")
            p("  2  Root Mode       (Execute with root permissions)")
            p("  3  Dry-Run Mode    (Preview commands without executing)")
            p("\n  0  Exit\n")

        mode_choice = input("  → ").strip()

        if mode_choice == "0":
            return
        elif mode_choice not in ("1", "2", "3"):
            if RICH and console:
                console.print("\n  [red]✗[/red] Invalid option\n", style="bold")
            else:
                p("\n  ✗ Invalid option\n")
            pause()
            return

        # Mode selected: 1=Normal, 2=Root, 3=Dry-Run
        # If Root Mode selected, request sudo and re-execute
        if mode_choice == "2":
            if RICH and console:
                console.print("\n  [yellow]→[/yellow] [bold]Requesting root permissions...[/bold]\n")
                console.print("  Root Mode requires elevated permissions.\n")
            else:
                p("\n  → Requesting root permissions...\n")
                p("  Root Mode requires elevated permissions.\n")

            # This will re-execute the program with sudo
            # When it comes back, is_root() will be True and dry_run_mode will be False
            maybe_reexec_with_sudo()
            # If we reach here, user declined sudo or it failed
            return

        # If Dry-Run Mode selected, explain why root is needed and request sudo
        elif mode_choice == "3":
            if RICH and console:
                console.print("\n  [yellow]ℹ[/yellow]  [bold]Dry-Run Mode necesita permisos root para:[/bold]")
                console.print("     • Analizar el sistema completo")
                console.print("     • Leer logs de Docker")
                console.print("     • Calcular espacio recuperable con precisión")
                console.print("")
                console.print("  [dim]NO ejecutará ningún comando destructivo.[/dim]")
                console.print("  [dim]Solo mostrará qué haría en Root Mode.[/dim]\n")
            else:
                p("\n  ℹ  Dry-Run Mode necesita permisos root para:")
                p("     • Analizar el sistema completo")
                p("     • Leer logs de Docker")
                p("     • Calcular espacio recuperable con precisión")
                p("")
                p("  NO ejecutará ningún comando destructivo.")
                p("  Solo mostrará qué haría en Root Mode.\n")

            # This will re-execute the program with sudo and set dry-run env var
            # When it comes back, is_root() will be True and dry_run_mode will be True
            maybe_reexec_with_sudo(dry_run=True)
            # If we reach here, user declined sudo or it failed
            return

        # Normal Mode (mode_choice == "1")
        else:
            dry_run_mode = False

    # ═══════════════════════════════════════════════════════════
    # STEP 2: Main Menu Loop (with selected mode)
    # ═══════════════════════════════════════════════════════════
    while True:
        clear_screen()
        print_header()
        print_banner(banner_style="cyan", url_style="cyan")

        if RICH and console:
            console.print("\n[bold white]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/bold white]")
        else:
            p("\n═══════════════════════════════════════════════════════════")

        print_mode_banner(dry_run_mode)

        if RICH and console:
            console.print("[bold white]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/bold white]")
        else:
            p("═══════════════════════════════════════════════════════════")

        # Build dynamic menu with only available options
        menu_options = []
        option_num = 1

        # ── MONITORING & ANALYSIS ──
        print_category_header("🔵", "MONITORING & ANALYSIS")

        menu_options.append((option_num, "status_all"))
        if RICH and console:
            console.print(f"     [cyan]{option_num}[/cyan]   Status (System + Docker)")
        else:
            p(f"     {option_num}   Status (System + Docker)")
        option_num += 1

        menu_options.append((option_num, "status_system"))
        if RICH and console:
            console.print(f"     [cyan]{option_num}[/cyan]   Status System only")
        else:
            p(f"     {option_num}   Status System only")
        option_num += 1

        menu_options.append((option_num, "status_docker"))
        if RICH and console:
            console.print(f"     [cyan]{option_num}[/cyan]   Status Docker only")
        else:
            p(f"     {option_num}   Status Docker only")
        option_num += 1

        menu_options.append((option_num, "analyze"))
        if RICH and console:
            console.print(f"     [cyan]{option_num}[/cyan]   Analyze Disk Usage [dim](with TUI)[/dim]")
        else:
            p(f"     {option_num}   Analyze Disk Usage (with TUI)")
        option_num += 1

        # ── CLEANUP & MAINTENANCE ──
        print_category_header("🟢", "CLEANUP & MAINTENANCE")

        menu_options.append((option_num, "clean_docker"))
        if RICH and console:
            console.print(f"     [green]{option_num}[/green]   Clean Docker [dim](interactive)[/dim]")
        else:
            p(f"     {option_num}   Clean Docker (interactive)")
        option_num += 1

        menu_options.append((option_num, "clean_system"))
        if RICH and console:
            console.print(f"     [green]{option_num}[/green]   Clean System [dim](interactive)[/dim]")
        else:
            p(f"     {option_num}   Clean System (interactive)")
        option_num += 1

        menu_options.append((option_num, "purge"))
        if RICH and console:
            console.print(f"     [green]{option_num}[/green]   Purge Build Artifacts")
        else:
            p(f"     {option_num}   Purge Build Artifacts")
        option_num += 1

        menu_options.append((option_num, "installer"))
        if RICH and console:
            console.print(f"     [green]{option_num}[/green]   Remove Installer Files")
        else:
            p(f"     {option_num}   Remove Installer Files")
        option_num += 1

        # ── SYSTEM OPERATIONS ──
        print_category_header("🟡", "SYSTEM OPERATIONS")

        menu_options.append((option_num, "uninstall"))
        if RICH and console:
            console.print(f"     [yellow]{option_num}[/yellow]   Uninstall Applications")
        else:
            p(f"     {option_num}   Uninstall Applications")
        option_num += 1

        # Optimize System - Only in Root Mode
        if is_root():
            menu_options.append((option_num, "optimize"))
            if RICH and console:
                console.print(f"     [yellow]{option_num}[/yellow]   Optimize System")
            else:
                p(f"     {option_num}   Optimize System")
            option_num += 1

        # ── CONFIGURATION ──
        print_category_header("🟠", "CONFIGURATION")

        menu_options.append((option_num, "whitelist"))
        if RICH and console:
            console.print(f"    [bright_yellow]{option_num}[/bright_yellow]   Manage Whitelist")
        else:
            p(f"    {option_num}   Manage Whitelist")
        option_num += 1

        menu_options.append((option_num, "config"))
        if RICH and console:
            console.print(f"    [bright_yellow]{option_num}[/bright_yellow]   Manage Configuration")
        else:
            p(f"    {option_num}   Manage Configuration")
        option_num += 1

        # ── LINUXMOLE SYSTEM ──
        # Update and Self-Uninstall - Only in Root Mode
        if is_root():
            print_category_header("🔴", "LINUXMOLE SYSTEM")

            menu_options.append((option_num, "update"))
            if RICH and console:
                console.print(f"    [red]{option_num}[/red]   Update LinuxMole")
            else:
                p(f"    {option_num}   Update LinuxMole")
            option_num += 1

            menu_options.append((option_num, "self_uninstall"))
            if RICH and console:
                console.print(f"    [red]{option_num}[/red]   Self-Uninstall LinuxMole")
            else:
                p(f"    {option_num}   Self-Uninstall LinuxMole")
            option_num += 1

        # Footer
        p("")
        if RICH and console:
            console.print("[dim]─────────────────────────────────────────────────────────────[/dim]")
            console.print("    [bold white]0[/bold white]   Exit Program")
            console.print("[dim]─────────────────────────────────────────────────────────────[/dim]\n")
        else:
            p("─────────────────────────────────────────────────────────────")
            p("    0   Exit Program")
            p("─────────────────────────────────────────────────────────────\n")

        choice = input("  → ").strip()

        if choice == "0":
            if RICH and console:
                console.print("\n  [dim]Exiting LinuxMole...[/dim]\n")
            return

        # Convert input to integer and find corresponding action
        try:
            choice_num = int(choice)
        except ValueError:
            if RICH and console:
                console.print("\n  [red]✗[/red] Invalid option\n", style="bold")
            else:
                p("\n  ✗ Invalid option\n")
            pause()
            continue

        # Find the action for this choice number
        action = None
        for num, act in menu_options:
            if num == choice_num:
                action = act
                break

        if not action:
            if RICH and console:
                console.print("\n  [red]✗[/red] Invalid option\n", style="bold")
            else:
                p("\n  ✗ Invalid option\n")
            pause()
            continue

        # Execute the selected action
        if action == "status_all":
            clear_screen()
            print_header()

            # Check root requirement for Docker information
            if not is_root() and which("docker") and not dry_run_mode:
                if RICH and console:
                    console.print("\n  [yellow]ℹ  Root Mode required for complete Docker information[/yellow]")
                    console.print("     [yellow]Some Docker logs and details may not be available in Normal Mode[/yellow]\n")
                else:
                    p("\n  ℹ  Root Mode required for complete Docker information")
                    p("     Some Docker logs and details may not be available in Normal Mode\n")

            args = argparse.Namespace(paths=False, top_logs=20)
            cmd_status_all(args)
            pause()

        elif action == "status_system":
            clear_screen()
            print_header()
            args = argparse.Namespace(paths=False)
            cmd_status_system(args)
            pause()

        elif action == "status_docker":
            clear_screen()
            print_header()

            # Check root requirement
            if not is_root() and which("docker") and not dry_run_mode:
                if RICH and console:
                    console.print("\n  [yellow]ℹ  Root Mode required for complete Docker information[/yellow]")
                    console.print("     [yellow]Some Docker logs and details may not be available in Normal Mode[/yellow]\n")
                else:
                    p("\n  ℹ  Root Mode required for complete Docker information")
                    p("     Some Docker logs and details may not be available in Normal Mode\n")

            args = argparse.Namespace(top_logs=20)
            cmd_docker_status(args)
            pause()

        elif action == "analyze":
            clear_screen()
            print_header()
            simple_analyze()
            pause()

        # ── CLEANUP & MAINTENANCE ──
        elif action == "clean_docker":
            clear_screen()
            print_header()

            # Root required for Docker cleanup
            if not is_root() and not dry_run_mode:
                if RICH and console:
                    console.print("\n  [red]⚠[/red]  [bold red]Root Mode required for Docker cleanup operations[/bold red]")
                    console.print("     Please restart LinuxMole in Root Mode to use this feature\n")
                else:
                    p("\n  ⚠  Root Mode required for Docker cleanup operations")
                    p("     Please restart LinuxMole in Root Mode to use this feature\n")
                pause()
                continue

            simple_docker_clean(dry_run_mode)
            pause()

        elif action == "clean_system":
            clear_screen()
            print_header()

            # Root required for system cleanup
            if not is_root() and not dry_run_mode:
                if RICH and console:
                    console.print("\n  [red]⚠[/red]  [bold red]Root Mode required for system cleanup operations[/bold red]")
                    console.print("     Please restart LinuxMole in Root Mode to use this feature\n")
                else:
                    p("\n  ⚠  Root Mode required for system cleanup operations")
                    p("     Please restart LinuxMole in Root Mode to use this feature\n")
                pause()
                continue

            simple_clean_system(dry_run_mode)
            pause()

        elif action == "purge":
            clear_screen()
            print_header()
            simple_purge()
            pause()

        elif action == "installer":
            clear_screen()
            print_header()
            simple_installer()
            pause()

        # ── SYSTEM OPERATIONS ──
        elif action == "uninstall":
            clear_screen()
            print_header()
            simple_uninstall(dry_run_mode)
            pause()

        elif action == "optimize":
            clear_screen()
            print_header()
            simple_optimize(dry_run_mode)
            pause()

        # ── CONFIGURATION ──
        elif action == "whitelist":
            simple_whitelist()  # Ya tiene su propio loop

        elif action == "config":
            simple_config()

        # ── LINUXMOLE SYSTEM ──
        elif action == "update":
            simple_update()

        elif action == "self_uninstall":
            simple_self_uninstall()
