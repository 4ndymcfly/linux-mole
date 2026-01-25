#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Docker size parsing and formatting functions for LinuxMole.
"""

from __future__ import annotations
import re
from typing import Dict, List, Optional, Tuple

from linuxmole.constants import _SIZE_RE


def parse_size_to_bytes(s: str) -> Optional[int]:
    """Parse a size string (e.g., '1.5GB') to bytes."""
    if not s:
        return None
    m = _SIZE_RE.match(s)
    if not m:
        return None
    val = float(m.group(1))
    unit = (m.group(2) or "B").upper()
    factors = {
        "B": 1,
        "KB": 1000,
        "MB": 1000 ** 2,
        "GB": 1000 ** 3,
        "TB": 1000 ** 4,
        "PB": 1000 ** 5,
        "KIB": 1024,
        "MIB": 1024 ** 2,
        "GIB": 1024 ** 3,
        "TIB": 1024 ** 4,
        "PIB": 1024 ** 5,
    }
    if unit not in factors:
        return None
    return int(val * factors[unit])


def parse_journal_usage_bytes(s: str) -> Optional[int]:
    """Parse journal usage string to bytes."""
    m = re.search(r"([0-9]+(?:\.[0-9]+)?\s*[KMGTP]i?B)", s, re.IGNORECASE)
    if not m:
        return None
    return parse_size_to_bytes(m.group(1))


def sum_image_sizes(imgs: List[Dict]) -> int:
    """Calculate total size of images."""
    total = 0
    for it in imgs:
        size_str = (it.get("Size") or "").strip()
        b = parse_size_to_bytes(size_str)
        if b is not None:
            total += b
    return total


def parse_container_size(size_str: str) -> Optional[int]:
    """Parse container size string to bytes."""
    if not size_str:
        return None
    first = size_str.split()[0]
    return parse_size_to_bytes(first)


def sum_container_sizes(containers: List[Dict]) -> Tuple[int, int]:
    """Calculate total size of containers and count unknown sizes."""
    total = 0
    unknown = 0
    for it in containers:
        size_str = (it.get("Size") or "").strip()
        b = parse_container_size(size_str)
        if b is None:
            unknown += 1
        else:
            total += b
    return total, unknown
