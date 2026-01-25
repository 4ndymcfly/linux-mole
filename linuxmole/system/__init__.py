#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
System utilities for LinuxMole.
"""

from __future__ import annotations

from linuxmole.system.metrics import (
    disk_usage_bytes,
    mem_usage_bytes,
    mem_stats_bytes,
    read_diskstats,
    disk_io_rate,
    read_netdev,
    net_io_rate,
    read_cpu_times,
    cpu_usage_percent,
    top_processes,
)

from linuxmole.system.apt import (
    apt_autoremove_count,
    list_installed_kernels,
    kernel_version_from_pkg,
    sort_versions_dpkg,
    kernel_cleanup_candidates,
    kernel_pkg_size_bytes,
    systemctl_failed_units,
    reboot_required,
)

from linuxmole.system.paths import (
    du_size,
    du_bytes,
    size_path_bytes,
    list_installer_files,
    find_log_candidates,
    parse_path_entries,
    analyze_paths,
)

__all__ = [
    # metrics
    "disk_usage_bytes",
    "mem_usage_bytes",
    "mem_stats_bytes",
    "read_diskstats",
    "disk_io_rate",
    "read_netdev",
    "net_io_rate",
    "read_cpu_times",
    "cpu_usage_percent",
    "top_processes",
    # apt
    "apt_autoremove_count",
    "list_installed_kernels",
    "kernel_version_from_pkg",
    "sort_versions_dpkg",
    "kernel_cleanup_candidates",
    "kernel_pkg_size_bytes",
    "systemctl_failed_units",
    "reboot_required",
    # paths
    "du_size",
    "du_bytes",
    "size_path_bytes",
    "list_installer_files",
    "find_log_candidates",
    "parse_path_entries",
    "analyze_paths",
]
