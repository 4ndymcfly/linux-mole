#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Command implementations for LinuxMole.
"""

from __future__ import annotations

from linuxmole.commands.status import (
    cmd_status_system,
    cmd_status_all,
    cmd_docker_status,
)

from linuxmole.commands.clean import (
    cmd_clean_all,
    cmd_clean_system,
    cmd_docker_clean,
    apply_default_clean_flags,
)

from linuxmole.commands.analyze import (
    cmd_analyze,
)

from linuxmole.commands.purge import (
    cmd_purge,
)

from linuxmole.commands.installer import (
    cmd_installer,
)

from linuxmole.commands.uninstall import (
    cmd_uninstall_app,
    is_apt_package,
    is_snap_package,
    is_flatpak_package,
    get_package_config_paths,
)

from linuxmole.commands.optimize import (
    cmd_optimize,
)

from linuxmole.commands.whitelist import (
    cmd_whitelist,
)

from linuxmole.commands.config_cmd import (
    cmd_config,
)

__all__ = [
    # status
    "cmd_status_system",
    "cmd_status_all",
    "cmd_docker_status",
    # clean
    "cmd_clean_all",
    "cmd_clean_system",
    "cmd_docker_clean",
    "apply_default_clean_flags",
    # analyze
    "cmd_analyze",
    # purge
    "cmd_purge",
    # installer
    "cmd_installer",
    # uninstall
    "cmd_uninstall_app",
    "is_apt_package",
    "is_snap_package",
    "is_flatpak_package",
    "get_package_config_paths",
    # optimize
    "cmd_optimize",
    # whitelist
    "cmd_whitelist",
    # config
    "cmd_config",
]
