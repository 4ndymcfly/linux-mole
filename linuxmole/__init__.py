#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LinuxMole - Safe maintenance for Linux + Docker.
"""

from __future__ import annotations

# Re-export constants (LAYER 0)
from linuxmole.constants import (
    BANNER,
    PROJECT_URL,
    TAGLINE,
    VERSION,
    _SIZE_RE,
    RICH,
    TEXTUAL,
    console,
)

# Re-export logging (LAYER 0)
from linuxmole.logging_setup import (
    logger,
    setup_logging,
)

# Re-export output (LAYER 1)
from linuxmole.output import (
    p,
    title,
    print_banner,
    print_header,
    section,
    line_ok,
    line_do,
    line_skip,
    line_warn,
    kv_table,
    table,
    scan_status,
)

# Re-export helpers (LAYER 1)
from linuxmole.helpers import (
    which,
    run,
    capture,
    is_root,
    confirm,
    human_bytes,
    format_size,
    bar,
    now_str,
    clear_screen,
    pause,
    maybe_reexec_with_sudo,
)

# Re-export config (LAYER 1)
from linuxmole.config import (
    config_dir,
    whitelist_path,
    purge_paths_file,
    config_file_path,
    default_config,
    load_config,
    save_config,
    load_whitelist,
    is_whitelisted,
    ensure_config_files,
    load_purge_paths,
)

# Re-export plans (LAYER 1)
from linuxmole.plans import (
    Action,
    show_plan,
    exec_actions,
)

# Re-export system (LAYER 2)
from linuxmole.system import (
    # metrics
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
    # apt
    apt_autoremove_count,
    list_installed_kernels,
    kernel_version_from_pkg,
    sort_versions_dpkg,
    kernel_cleanup_candidates,
    kernel_pkg_size_bytes,
    systemctl_failed_units,
    reboot_required,
    # paths
    du_size,
    du_bytes,
    size_path_bytes,
    list_installer_files,
    find_log_candidates,
    parse_path_entries,
    analyze_paths,
)

# Re-export docker (LAYER 2)
from linuxmole.docker import (
    # inspect
    docker_available,
    docker_cmd,
    docker_json_lines,
    docker_ps_all,
    docker_images_all,
    docker_images_dangling,
    docker_networks,
    docker_volumes,
    docker_networks_dangling,
    docker_volumes_dangling,
    docker_volume_mountpoints,
    docker_system_df,
    docker_builder_df,
    docker_container_image_ids,
    compute_unused_images,
    docker_stopped_containers,
    cap_containers,
    cap_networks,
    cap_imgs,
    # logs
    docker_default_log_dir,
    can_read_docker_logs,
    docker_logs_dir_exists,
    docker_container_log_paths,
    stat_logs,
    total_logs_size,
    list_all_logs,
    truncate_file,
    # formatting
    parse_size_to_bytes,
    parse_journal_usage_bytes,
    sum_image_sizes,
    parse_container_size,
    sum_container_sizes,
)

# Re-export commands (LAYER 3)
from linuxmole.commands import (
    # status
    cmd_status_system,
    cmd_status_all,
    cmd_docker_status,
    # clean
    cmd_clean_all,
    cmd_clean_system,
    cmd_docker_clean,
    apply_default_clean_flags,
    # analyze
    cmd_analyze,
    # purge
    cmd_purge,
    # installer
    cmd_installer,
    # uninstall
    cmd_uninstall_app,
    is_apt_package,
    is_snap_package,
    is_flatpak_package,
    get_package_config_paths,
    # optimize
    cmd_optimize,
    # whitelist
    cmd_whitelist,
    # config
    cmd_config,
)

# Re-export interactive (LAYER 4)
from linuxmole.interactive import (
    prompt_bool,
    prompt_choice,
    prompt_int,
    simple_docker_clean,
    simple_clean_system,
    interactive_simple,
)

# Re-export cli (LAYER 4)
from linuxmole.cli import (
    print_help,
    main,
)

__all__ = [
    # Constants
    "BANNER",
    "PROJECT_URL",
    "TAGLINE",
    "VERSION",
    "_SIZE_RE",
    "RICH",
    "TEXTUAL",
    "console",
    # Logging
    "logger",
    "setup_logging",
    # Output
    "p",
    "title",
    "print_banner",
    "print_header",
    "section",
    "line_ok",
    "line_do",
    "line_skip",
    "line_warn",
    "kv_table",
    "table",
    "scan_status",
    # Helpers
    "which",
    "run",
    "capture",
    "is_root",
    "confirm",
    "human_bytes",
    "format_size",
    "bar",
    "now_str",
    "clear_screen",
    "pause",
    "maybe_reexec_with_sudo",
    # Config
    "config_dir",
    "whitelist_path",
    "purge_paths_file",
    "config_file_path",
    "default_config",
    "load_config",
    "save_config",
    "load_whitelist",
    "is_whitelisted",
    "ensure_config_files",
    "load_purge_paths",
    # Plans
    "Action",
    "show_plan",
    "exec_actions",
    # System - metrics
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
    # System - apt
    "apt_autoremove_count",
    "list_installed_kernels",
    "kernel_version_from_pkg",
    "sort_versions_dpkg",
    "kernel_cleanup_candidates",
    "kernel_pkg_size_bytes",
    "systemctl_failed_units",
    "reboot_required",
    # System - paths
    "du_size",
    "du_bytes",
    "size_path_bytes",
    "list_installer_files",
    "find_log_candidates",
    "parse_path_entries",
    "analyze_paths",
    # Docker - inspect
    "docker_available",
    "docker_cmd",
    "docker_json_lines",
    "docker_ps_all",
    "docker_images_all",
    "docker_images_dangling",
    "docker_networks",
    "docker_volumes",
    "docker_networks_dangling",
    "docker_volumes_dangling",
    "docker_volume_mountpoints",
    "docker_system_df",
    "docker_builder_df",
    "docker_container_image_ids",
    "compute_unused_images",
    "docker_stopped_containers",
    "cap_containers",
    "cap_networks",
    "cap_imgs",
    # Docker - logs
    "docker_default_log_dir",
    "can_read_docker_logs",
    "docker_logs_dir_exists",
    "docker_container_log_paths",
    "stat_logs",
    "total_logs_size",
    "list_all_logs",
    "truncate_file",
    # Docker - formatting
    "parse_size_to_bytes",
    "parse_journal_usage_bytes",
    "sum_image_sizes",
    "parse_container_size",
    "sum_container_sizes",
    # Commands - status
    "cmd_status_system",
    "cmd_status_all",
    "cmd_docker_status",
    # Commands - clean
    "cmd_clean_all",
    "cmd_clean_system",
    "cmd_docker_clean",
    "apply_default_clean_flags",
    # Commands - analyze
    "cmd_analyze",
    # Commands - purge
    "cmd_purge",
    # Commands - installer
    "cmd_installer",
    # Commands - uninstall
    "cmd_uninstall_app",
    "is_apt_package",
    "is_snap_package",
    "is_flatpak_package",
    "get_package_config_paths",
    # Commands - optimize
    "cmd_optimize",
    # Commands - whitelist
    "cmd_whitelist",
    # Commands - config
    "cmd_config",
    # Interactive
    "prompt_bool",
    "prompt_choice",
    "prompt_int",
    "simple_docker_clean",
    "simple_clean_system",
    "interactive_simple",
    # CLI
    "print_help",
    "main",
]
