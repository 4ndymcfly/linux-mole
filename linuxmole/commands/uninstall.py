#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Uninstall command implementation for LinuxMole.
"""

from __future__ import annotations
import argparse
import subprocess
from pathlib import Path
from typing import List

from linuxmole.logging_setup import logger
from linuxmole.output import section, p, line_ok, line_warn, table
from linuxmole.helpers import which, capture, confirm, is_root, run, maybe_reexec_with_sudo
from linuxmole.config import ensure_config_files, load_whitelist, is_whitelisted
from linuxmole.plans import Action, show_plan, exec_actions


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
            actions.append(Action(
                f"Remove package with configs",
                ["apt", "remove", "--purge", "-y", package],
                root=True
            ))
        else:
            actions.append(Action(
                f"Remove package",
                ["apt", "remove", "-y", package],
                root=True
            ))

        # Clean up user config paths if --purge
        if args.purge:
            config_paths = get_package_config_paths(package)
            if config_paths:
                for path in config_paths:
                    actions.append(Action(
                        f"Remove user config",
                        ["rm", "-rf", path],
                        root=False
                    ))

        # Autoremove after uninstall
        actions.append(Action(
            f"Clean up dependencies",
            ["apt", "autoremove", "-y"],
            root=True
        ))

    elif is_snap_package(package):
        pkg_manager = "Snap"
        p(f"Package '{package}' found via Snap")

        actions.append(Action(f"Remove snap", ["snap", "remove", package], root=True))

        # Snap data is in ~/snap/<package>
        snap_data = str(Path.home() / "snap" / package)
        if Path(snap_data).exists() and args.purge:
            actions.append(Action(
                f"Remove snap data",
                ["rm", "-rf", snap_data],
                root=False
            ))

    elif is_flatpak_package(package):
        pkg_manager = "Flatpak"
        p(f"Package '{package}' found via Flatpak")

        actions.append(Action(
            f"Remove flatpak",
            ["flatpak", "uninstall", "-y", package],
            root=False
        ))

        # Flatpak data is in ~/.var/app/<package>
        flatpak_data = str(Path.home() / ".var" / "app" / package)
        if Path(flatpak_data).exists() and args.purge:
            actions.append(Action(
                f"Remove flatpak data",
                ["rm", "-rf", flatpak_data],
                root=False
            ))

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
