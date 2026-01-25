#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Path analysis and file management functions for LinuxMole.
"""

from __future__ import annotations
import os
import re
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from linuxmole.helpers import which, capture


def du_size(path: str) -> Optional[str]:
    """Get human-readable size of a path using du."""
    if not which("du"):
        return None
    try:
        out = capture(["du", "-sh", path])
        return out.split()[0] if out else None
    except Exception:
        return None


def du_bytes(path: str) -> Optional[int]:
    """Get size of a path in bytes using du."""
    if not which("du"):
        return None
    try:
        out = capture(["du", "-sb", path])
        if not out:
            return None
        return int(out.split()[0])
    except Exception:
        return None


def size_path_bytes(path: Path) -> Optional[int]:
    """Get size of a path in bytes."""
    return du_bytes(str(path))


def list_installer_files() -> List[Tuple[str, int]]:
    """Find installer files in common locations."""
    exts = (".deb", ".rpm", ".AppImage", ".run", ".tar.gz", ".tgz", ".zip", ".iso")
    locations = [Path("~/Downloads").expanduser(), Path("~/Desktop").expanduser()]
    res: List[Tuple[str, int]] = []
    for base in locations:
        if not base.exists():
            continue
        for p in base.rglob("*"):
            if not p.is_file():
                continue
            name = p.name
            if name.endswith(exts):
                try:
                    res.append((str(p), p.stat().st_size))
                except Exception:
                    continue
    res.sort(key=lambda x: x[1], reverse=True)
    return res


def find_log_candidates(days: int) -> List[Tuple[str, int]]:
    """Find old/rotated log files that can be cleaned."""
    base = Path("/var/log")
    if not base.exists():
        return []
    cutoff = time.time() - (days * 86400)
    patterns = (".gz", ".old", ".1", ".2", ".3", ".4", ".5", ".6", ".7", ".8", ".9")
    res: List[Tuple[str, int]] = []
    for path in base.rglob("*"):
        if not path.is_file():
            continue
        name = path.name
        if not (name.endswith(patterns) or re.search(r"\.\d+\.gz$", name)):
            continue
        try:
            st = path.stat()
        except Exception:
            continue
        if st.st_mtime < cutoff:
            res.append((str(path), st.st_size))
    res.sort(key=lambda x: x[1], reverse=True)
    return res


def parse_path_entries(raw: str) -> List[str]:
    """Parse PATH environment variable into entries."""
    return [p for p in raw.split(":") if p]


def analyze_paths() -> Dict[str, List[str]]:
    """Analyze PATH environment variable for issues."""
    env_path = os.environ.get("PATH", "")
    entries = [os.path.expanduser(os.path.expandvars(p)) for p in parse_path_entries(env_path)]
    seen = set()
    dup = []
    missing = []
    for pth in entries:
        if pth in seen:
            dup.append(pth)
        else:
            seen.add(pth)
        if not os.path.isdir(pth):
            missing.append(pth)

    rc_files = [
        Path("~/.zshrc").expanduser(),
        Path("~/.bashrc").expanduser(),
        Path("~/.profile").expanduser(),
        Path("~/.bash_profile").expanduser(),
        Path("/etc/profile"),
        Path("/etc/zshrc"),
    ]
    rc_hits = []
    for fp in rc_files:
        if not fp.exists():
            continue
        try:
            for line in fp.read_text(encoding="utf-8", errors="ignore").splitlines():
                if "PATH=" in line or "export PATH" in line:
                    rc_hits.append(f"{fp}: {line.strip()}")
        except Exception:
            continue

    return {
        "entries": entries,
        "duplicates": dup,
        "missing": missing,
        "rc_hits": rc_hits,
    }
