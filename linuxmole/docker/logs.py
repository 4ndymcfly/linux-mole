#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Docker logs management functions for LinuxMole.
"""

from __future__ import annotations
import os
from pathlib import Path
from typing import List, Tuple

from linuxmole.output import p


def docker_default_log_dir() -> Path:
    """Get default Docker logs directory."""
    return Path("/var/lib/docker/containers")


def can_read_docker_logs() -> bool:
    """Check if we can read Docker logs directory."""
    base = docker_default_log_dir()
    try:
        return base.exists() and os.access(base, os.R_OK | os.X_OK)
    except Exception:
        return False


def docker_logs_dir_exists() -> bool:
    """Check if Docker logs directory exists."""
    base = docker_default_log_dir()
    try:
        return base.exists()
    except Exception:
        return False


def docker_container_log_paths() -> List[Tuple[str, Path]]:
    """
    Return list of (container_id, log_path) for json-file logs, if present.
    """
    base = docker_default_log_dir()
    res = []
    try:
        if not base.exists():
            return res
    except PermissionError:
        return res
    try:
        for d in base.iterdir():
            if not d.is_dir():
                continue
            cid = d.name
            logp = d / f"{cid}-json.log"
            if logp.exists():
                res.append((cid, logp))
    except PermissionError:
        return res
    return res


def stat_logs(top_n: int = 20) -> List[Tuple[str, Path, int]]:
    """Get top N largest log files."""
    items = []
    for cid, logp in docker_container_log_paths():
        try:
            sz = logp.stat().st_size
            items.append((cid, logp, sz))
        except Exception:
            pass
    items.sort(key=lambda x: x[2], reverse=True)
    return items[:top_n]


def total_logs_size() -> Tuple[int, int]:
    """Get total size and count of all container logs."""
    total = 0
    count = 0
    for _, logp in docker_container_log_paths():
        try:
            total += logp.stat().st_size
            count += 1
        except Exception:
            pass
    return total, count


def list_all_logs() -> List[Tuple[str, Path, int]]:
    """Get all container logs with their sizes."""
    items = []
    for cid, logp in docker_container_log_paths():
        try:
            items.append((cid, logp, logp.stat().st_size))
        except Exception:
            pass
    return items


def truncate_file(path: Path, dry_run: bool) -> None:
    """Truncate a file to zero size."""
    if dry_run:
        p(f"[dry-run] truncate -s 0 {path}")
        return
    try:
        with open(path, "w", encoding="utf-8"):
            pass
        p(f"[ok] truncated {path}")
    except Exception as e:
        p(f"[error] truncate {path}: {e}")
