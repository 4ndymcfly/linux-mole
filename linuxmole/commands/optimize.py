#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Optimize command implementation for LinuxMole.
"""

from __future__ import annotations
import argparse

from linuxmole.logging_setup import logger
from linuxmole.output import section, p, line_ok, line_warn
from linuxmole.helpers import which, capture, confirm, is_root, maybe_reexec_with_sudo
from linuxmole.plans import Action, show_plan, exec_actions
from linuxmole.config import load_config


def cmd_optimize(args: argparse.Namespace) -> None:
    """Optimize system by rebuilding databases and restarting services."""
    section("System Optimization")

    # Load config
    config = load_config()
    optimize_config = config.get("optimize", {})

    actions = []

    # Determine what to optimize
    optimize_all = args.all or not (
        args.database or args.network or args.services or args.clear_cache
    )

    # When using --all, respect config flags to enable/disable specific optimizations
    if optimize_all:
        should_database = optimize_config.get("auto_database", True)
        should_network = optimize_config.get("auto_network", True)
        should_services = optimize_config.get("auto_services", True)
    else:
        # When specific flags are used, use them directly
        should_database = args.database
        should_network = args.network
        should_services = args.services

    # 1. Database optimization
    if should_database:
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
            actions.append(Action(
                "Update MIME database",
                ["update-mime-database", "/usr/share/mime"],
                root=True
            ))

        # update-desktop-database
        if which("update-desktop-database"):
            actions.append(Action(
                "Update desktop database",
                ["update-desktop-database"],
                root=True
            ))

    # 2. Network optimization
    if should_network:
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
                    actions.append(Action(
                        "Restart NetworkManager",
                        ["systemctl", "restart", "NetworkManager"],
                        root=True
                    ))
            except Exception:
                pass

        # Clear ARP cache
        if which("ip"):
            actions.append(Action(
                "Clear ARP cache",
                ["ip", "-s", "-s", "neigh", "flush", "all"],
                root=True
            ))

    # 3. Services optimization
    if should_services:
        logger.info("Adding services optimization tasks")

        if which("systemctl"):
            # Reload systemd daemon
            actions.append(Action(
                "Reload systemd daemon",
                ["systemctl", "daemon-reload"],
                root=True
            ))

            # Reset failed units
            actions.append(Action(
                "Reset failed systemd units",
                ["systemctl", "reset-failed"],
                root=True
            ))

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
            actions.append(Action(
                "Clear page cache",
                ["sh", "-c", "echo 3 > /proc/sys/vm/drop_caches"],
                root=True
            ))
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
