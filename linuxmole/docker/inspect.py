#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Docker inspection and management functions for LinuxMole.
"""

from __future__ import annotations
import json
from typing import Dict, List, Set, Tuple

from linuxmole.helpers import which, capture


def docker_available() -> bool:
    """Check if Docker is available."""
    return which("docker") is not None


def docker_cmd(args: List[str]) -> List[str]:
    """Build a docker command with arguments."""
    return ["docker", *args]


def docker_json_lines(args: List[str]) -> List[Dict]:
    """
    Execute docker command with JSON-per-line format (via --format '{{json .}}').
    """
    out = capture(docker_cmd(args))
    if not out:
        return []
    lines = out.splitlines()
    res = []
    for ln in lines:
        try:
            res.append(json.loads(ln))
        except Exception:
            # If docker prints non-json, ignore that line
            pass
    return res


def docker_ps_all() -> List[Dict]:
    """Get all containers (running + stopped)."""
    return docker_json_lines(["ps", "-a", "--size", "--no-trunc", "--format", "{{json .}}"])


def docker_images_all() -> List[Dict]:
    """Get all images."""
    return docker_json_lines(["images", "-a", "--no-trunc", "--format", "{{json .}}"])


def docker_images_dangling() -> List[Dict]:
    """Get dangling images."""
    return docker_json_lines(["images", "-f", "dangling=true", "--no-trunc", "--format", "{{json .}}"])


def docker_networks() -> List[Dict]:
    """Get all networks."""
    return docker_json_lines(["network", "ls", "--no-trunc", "--format", "{{json .}}"])


def docker_volumes() -> List[Dict]:
    """Get all volumes."""
    return docker_json_lines(["volume", "ls", "--format", "{{json .}}"])


def docker_networks_dangling() -> List[Dict]:
    """Get dangling networks."""
    return docker_json_lines(["network", "ls", "-f", "dangling=true", "--no-trunc", "--format", "{{json .}}"])


def docker_volumes_dangling() -> List[Dict]:
    """Get dangling volumes."""
    return docker_json_lines(["volume", "ls", "-f", "dangling=true", "--format", "{{json .}}"])


def docker_volume_mountpoints(names: List[str]) -> Dict[str, str]:
    """Get mountpoints for specified volumes."""
    if not names:
        return {}
    args = ["volume", "inspect", "--format", "{{.Name}} {{.Mountpoint}}", *names]
    try:
        out = capture(docker_cmd(args))
    except Exception:
        return {}
    res = {}
    for line in out.splitlines():
        parts = line.strip().split(maxsplit=1)
        if len(parts) == 2:
            res[parts[0]] = parts[1]
    return res


def docker_system_df() -> str:
    """Get docker system disk usage (human readable)."""
    return capture(docker_cmd(["system", "df"]))


def docker_builder_df() -> str:
    """Get docker builder disk usage."""
    return capture(docker_cmd(["builder", "du"]))


def docker_container_image_ids() -> List[str]:
    """
    Return image IDs used by any container (running or stopped).
    """
    ps = docker_ps_all()
    used = set()
    for c in ps:
        img = (c.get("Image") or "").strip()
        if img:
            used.add(img)
    return sorted(used)


def compute_unused_images() -> Tuple[List[Dict], List[Dict]]:
    """
    Return (dangling_images, unused_images_not_dangling).
    - dangling: docker images -f dangling=true
    - unused: images not referenced by any container (by repo:tag match or by ID prefix match)
    """
    all_imgs = docker_images_all()
    dangling = docker_images_dangling()
    used_refs = set(docker_container_image_ids())

    # Build sets for matching
    used_refs_lower = set(x.lower() for x in used_refs)

    unused = []
    for img in all_imgs:
        repo = (img.get("Repository") or "")
        tag = (img.get("Tag") or "")
        img_id = (img.get("ID") or "")
        repotag = f"{repo}:{tag}" if repo and tag and tag != "<none>" and repo != "<none>" else ""
        candidates = set()
        if repotag:
            candidates.add(repotag.lower())
        if img_id:
            candidates.add(img_id.lower())
            # also short id match
            candidates.add(img_id.lower().replace("sha256:", "")[:12])

        # If any candidate matches used_refs entries (which can be name:tag or id/shortid), treat as used
        is_used = False
        for u in used_refs_lower:
            # compare direct or prefix
            if u in candidates:
                is_used = True
                break
            # handle "sha256:..." and short prefixes
            if img_id and (u.startswith(img_id.lower().replace("sha256:", "")[:12]) or img_id.lower().endswith(u)):
                is_used = True
                break
            if repotag and u == repotag.lower():
                is_used = True
                break

        if not is_used:
            unused.append(img)

    # Remove those that are dangling from unused_not_dangling
    dangling_ids = set((d.get("ID") or "") for d in dangling)
    unused_not_dangling = [u for u in unused if (u.get("ID") or "") not in dangling_ids]

    return dangling, unused_not_dangling


def docker_stopped_containers() -> List[Dict]:
    """Get all stopped containers."""
    stopped = []
    for c in docker_ps_all():
        state = (c.get("State") or "").lower()
        if state != "running":
            stopped.append(c)
    return stopped


def cap_containers(cs: List[Dict], n: int) -> List[List[str]]:
    """Format containers for display (limit to n)."""
    rows = []
    for it in cs[:n]:
        rows.append([
            (it.get("ID") or "")[:12],
            (it.get("Names") or ""),
            (it.get("Status") or ""),
            (it.get("Size") or ""),
        ])
    return rows


def cap_networks(nets: List[Dict], n: int) -> List[List[str]]:
    """Format networks for display (limit to n)."""
    rows = []
    for it in nets[:n]:
        rows.append([
            (it.get("ID") or "")[:12],
            (it.get("Name") or ""),
            (it.get("Driver") or ""),
        ])
    return rows


def cap_imgs(imgs: List[Dict], n: int) -> List[List[str]]:
    """Format images for display (limit to n)."""
    rows = []
    for it in imgs[:n]:
        rows.append([
            (it.get("ID") or "")[:19],
            (it.get("Repository") or ""),
            (it.get("Tag") or ""),
            (it.get("Size") or ""),
            (it.get("CreatedSince") or ""),
        ])
    return rows
