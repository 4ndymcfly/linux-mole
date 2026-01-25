#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
APT and kernel management functions for LinuxMole.
"""

from __future__ import annotations
import subprocess
from functools import cmp_to_key
from pathlib import Path
from typing import List, Optional, Tuple

from linuxmole.helpers import which, capture


def apt_autoremove_count() -> Optional[int]:
    """Count packages that can be autoremoved."""
    if not which("apt-get"):
        return None
    try:
        out = capture(["apt-get", "-s", "autoremove"])
    except Exception:
        return None
    count = 0
    for line in out.splitlines():
        if line.startswith("Remv "):
            count += 1
    return count


def list_installed_kernels() -> List[Tuple[str, str]]:
    """List all installed kernel packages."""
    if not which("dpkg-query"):
        return []
    try:
        out = capture(["dpkg-query", "-W", "-f", "${Package} ${Version}\n", "linux-image-[0-9]*"])
    except Exception:
        return []
    res = []
    for line in out.splitlines():
        parts = line.split()
        if len(parts) >= 2:
            res.append((parts[0], parts[1]))
    return res


def kernel_version_from_pkg(pkg: str) -> Optional[str]:
    """Extract kernel version from package name."""
    if not pkg.startswith("linux-image-"):
        return None
    return pkg.replace("linux-image-", "", 1)


def sort_versions_dpkg(versions: List[str]) -> List[str]:
    """Sort version strings using dpkg --compare-versions."""
    if not which("dpkg"):
        return versions
    def _cmp(a: str, b: str) -> int:
        if a == b:
            return 0
        try:
            subprocess.check_call(["dpkg", "--compare-versions", a, "gt", b])
            return 1
        except Exception:
            return -1
    return sorted(versions, key=cmp_to_key(_cmp))


def kernel_cleanup_candidates(keep: int = 2) -> List[str]:
    """Get list of old kernel packages that can be removed."""
    current = capture(["uname", "-r"])
    pkgs = list_installed_kernels()
    versions = []
    by_version = {}
    for pkg, ver in pkgs:
        kv = kernel_version_from_pkg(pkg)
        if not kv:
            continue
        versions.append(kv)
        by_version[kv] = pkg
    if not versions:
        return []
    versions_sorted = sort_versions_dpkg(versions)
    keep_set = set(versions_sorted[-keep:])
    keep_set.add(current)
    candidates = [by_version[v] for v in versions_sorted if v not in keep_set]
    return candidates


def kernel_pkg_size_bytes(pkgs: List[str]) -> Optional[int]:
    """Calculate total size of kernel packages."""
    if not pkgs or not which("dpkg-query"):
        return None
    total = 0
    for pkg in pkgs:
        try:
            out = capture(["dpkg-query", "-W", "-f", "${Installed-Size}", pkg])
            total += int(out.strip()) * 1024
        except Exception:
            return None
    return total


def systemctl_failed_units() -> Optional[List[str]]:
    """Get list of failed systemd units."""
    if not which("systemctl"):
        return None
    try:
        out = capture(["systemctl", "--failed", "--no-legend", "--no-pager"])
    except Exception:
        return None
    units = []
    for line in out.splitlines():
        parts = line.split()
        if len(parts) >= 4 and parts[2].lower() == "failed":
            units.append(parts[0])
    return units


def reboot_required() -> bool:
    """Check if system reboot is required."""
    return Path("/var/run/reboot-required").exists()
