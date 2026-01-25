#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Docker utilities for LinuxMole.
"""

from __future__ import annotations

from linuxmole.docker.inspect import (
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
)

from linuxmole.docker.logs import (
    docker_default_log_dir,
    can_read_docker_logs,
    docker_logs_dir_exists,
    docker_container_log_paths,
    stat_logs,
    total_logs_size,
    list_all_logs,
    truncate_file,
)

from linuxmole.docker.formatting import (
    parse_size_to_bytes,
    parse_journal_usage_bytes,
    sum_image_sizes,
    parse_container_size,
    sum_container_sizes,
)

__all__ = [
    # inspect
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
    # logs
    "docker_default_log_dir",
    "can_read_docker_logs",
    "docker_logs_dir_exists",
    "docker_container_log_paths",
    "stat_logs",
    "total_logs_size",
    "list_all_logs",
    "truncate_file",
    # formatting
    "parse_size_to_bytes",
    "parse_journal_usage_bytes",
    "sum_image_sizes",
    "parse_container_size",
    "sum_container_sizes",
]
