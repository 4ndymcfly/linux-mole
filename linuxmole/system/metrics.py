#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
System metrics collection for LinuxMole.
"""

from __future__ import annotations
import time
from typing import Dict, List, Optional, Tuple

from linuxmole.helpers import capture, which


def disk_usage_bytes(path: str = "/") -> Optional[Tuple[int, int, int]]:
    """Get disk usage for a path."""
    try:
        out = capture(["df", "-B1", path])
    except Exception:
        return None
    lines = out.splitlines()
    if len(lines) < 2:
        return None
    parts = lines[1].split()
    if len(parts) < 6:
        return None
    try:
        total = int(parts[1])
        used = int(parts[2])
        avail = int(parts[3])
        return total, used, avail
    except Exception:
        return None


def mem_usage_bytes() -> Optional[Tuple[int, int, int]]:
    """Get memory usage in bytes."""
    try:
        out = capture(["free", "-b"])
    except Exception:
        return None
    for line in out.splitlines():
        if line.lower().startswith("mem:"):
            parts = line.split()
            if len(parts) >= 4:
                try:
                    total = int(parts[1])
                    used = int(parts[2])
                    free = int(parts[3])
                    return total, used, free
                except Exception:
                    return None
    return None


def mem_stats_bytes() -> Optional[Tuple[int, int, int, int]]:
    """Get detailed memory statistics."""
    try:
        out = capture(["free", "-b"])
    except Exception:
        return None
    for line in out.splitlines():
        if line.lower().startswith("mem:"):
            parts = line.split()
            if len(parts) >= 7:
                try:
                    total = int(parts[1])
                    used = int(parts[2])
                    free = int(parts[3])
                    avail = int(parts[6])
                    return total, used, free, avail
                except Exception:
                    return None
    return None


def read_diskstats() -> Dict[str, Tuple[int, int]]:
    """Read disk statistics from /proc/diskstats."""
    res = {}
    try:
        with open("/proc/diskstats", "r", encoding="utf-8") as f:
            for line in f:
                parts = line.split()
                if len(parts) < 14:
                    continue
                name = parts[2]
                if name.startswith(("loop", "ram")):
                    continue
                sectors_read = int(parts[5])
                sectors_written = int(parts[9])
                res[name] = (sectors_read, sectors_written)
    except Exception:
        return {}
    return res


def disk_io_rate() -> Optional[Tuple[float, float]]:
    """Get disk I/O rate in bytes per second."""
    s1 = read_diskstats()
    if not s1:
        return None
    time.sleep(0.2)
    s2 = read_diskstats()
    if not s2:
        return None
    read_sec = 0
    write_sec = 0
    for k, (r2, w2) in s2.items():
        r1, w1 = s1.get(k, (0, 0))
        read_sec += max(0, r2 - r1)
        write_sec += max(0, w2 - w1)
    # 512 bytes per sector
    read_bps = (read_sec * 512) / 0.2
    write_bps = (write_sec * 512) / 0.2
    return read_bps, write_bps


def read_netdev() -> Dict[str, Tuple[int, int]]:
    """Read network device statistics from /proc/net/dev."""
    res = {}
    try:
        with open("/proc/net/dev", "r", encoding="utf-8") as f:
            for line in f:
                if ":" not in line:
                    continue
                iface, data = line.split(":", 1)
                iface = iface.strip()
                if iface == "lo":
                    continue
                parts = data.split()
                if len(parts) >= 16:
                    rx = int(parts[0])
                    tx = int(parts[8])
                    res[iface] = (rx, tx)
    except Exception:
        return {}
    return res


def net_io_rate() -> Optional[List[Tuple[str, float, float]]]:
    """Get network I/O rate in bytes per second."""
    s1 = read_netdev()
    if not s1:
        return None
    time.sleep(0.2)
    s2 = read_netdev()
    if not s2:
        return None
    res = []
    for iface, (rx2, tx2) in s2.items():
        rx1, tx1 = s1.get(iface, (0, 0))
        rx_bps = max(0, rx2 - rx1) / 0.2
        tx_bps = max(0, tx2 - tx1) / 0.2
        res.append((iface, rx_bps, tx_bps))
    res.sort(key=lambda x: (x[1] + x[2]), reverse=True)
    return res


def read_cpu_times() -> Optional[Tuple[int, int]]:
    """Read CPU times from /proc/stat."""
    try:
        with open("/proc/stat", "r", encoding="utf-8") as f:
            line = f.readline()
        parts = line.split()
        if parts[0] != "cpu":
            return None
        nums = [int(x) for x in parts[1:]]
        idle = nums[3] + nums[4] if len(nums) > 4 else nums[3]
        total = sum(nums)
        return total, idle
    except Exception:
        return None


def cpu_usage_percent() -> Optional[float]:
    """Get CPU usage percentage."""
    t1 = read_cpu_times()
    if not t1:
        return None
    time.sleep(0.2)
    t2 = read_cpu_times()
    if not t2:
        return None
    total1, idle1 = t1
    total2, idle2 = t2
    total_delta = total2 - total1
    idle_delta = idle2 - idle1
    if total_delta <= 0:
        return None
    return max(0.0, min(100.0, 100.0 * (1.0 - (idle_delta / total_delta))))


def top_processes(sort_key: str = "-%cpu", limit: int = 5) -> List[List[str]]:
    """Get top processes by CPU or memory usage."""
    if not which("ps"):
        return []
    try:
        out = capture(["ps", "-eo", "pid,comm,%cpu,%mem", f"--sort={sort_key}"])
    except Exception:
        return []
    rows = []
    for line in out.splitlines()[1:limit + 1]:
        parts = line.split(None, 3)
        if len(parts) >= 4:
            rows.append(parts)
    return rows
