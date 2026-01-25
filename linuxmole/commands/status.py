#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Status command implementations for LinuxMole.
"""

from __future__ import annotations
import argparse
import subprocess

from linuxmole.constants import RICH, console
from linuxmole.output import (
    section,
    p,
    line_do,
    line_ok,
    line_skip,
    line_warn,
    kv_table,
    table,
    scan_status,
)
from linuxmole.helpers import (
    capture,
    which,
    format_size,
    now_str,
    bar,
    maybe_reexec_with_sudo,
    is_root,
    human_bytes,
)
from linuxmole.system.metrics import (
    mem_usage_bytes,
    disk_usage_bytes,
    mem_stats_bytes,
    cpu_usage_percent,
    disk_io_rate,
    net_io_rate,
    top_processes,
)
from linuxmole.system.apt import (
    apt_autoremove_count,
    kernel_cleanup_candidates,
    systemctl_failed_units,
    reboot_required,
)
from linuxmole.system.paths import du_size, analyze_paths
from linuxmole.docker.inspect import (
    docker_available,
    docker_ps_all,
    docker_images_all,
    docker_volumes,
    docker_system_df,
    docker_builder_df,
    compute_unused_images,
    cap_imgs,
)
from linuxmole.docker.logs import docker_logs_dir_exists, can_read_docker_logs, stat_logs


def cmd_status_system(_: argparse.Namespace) -> None:
    section("System status")
    with scan_status("Scanning system..."):
        rows = [("Timestamp", now_str())]
        try:
            rows.append(("Uptime", capture(["uptime", "-p"])))
        except Exception:
            rows.append(("Uptime", "n/a"))
        try:
            rows.append(("Load", capture(["cat", "/proc/loadavg"])))
        except Exception:
            rows.append(("Load", "n/a"))
        mem_b = mem_usage_bytes()
        disk_b = disk_usage_bytes("/")
        mem_stats = mem_stats_bytes()
    kv_table("Summary", rows)
    if mem_b and disk_b:
        mem_total, mem_used, _ = mem_b
        disk_total, disk_used, disk_avail = disk_b
        line_do(f"System: RAM {format_size(mem_used)}/{format_size(mem_total)} | Disk {format_size(disk_used)}/{format_size(disk_total)} | Free {format_size(disk_avail)}")

    if mem_stats:
        total, used, free, avail = mem_stats
        table("Memory", ["Total", "Used", "Free", "Available"], [[
            format_size(total), format_size(used), format_size(free), format_size(avail)
        ]])

    section("Health snapshot")
    with scan_status("Scanning CPU/memory/disk..."):
        cpu = cpu_usage_percent()
        mem_b = mem_usage_bytes()
        disk_b = disk_usage_bytes("/")
    if cpu is not None:
        line_do(f"{'CPU':<7}{bar(cpu)}  {cpu:5.1f}%")
    else:
        line_skip("CPU usage unavailable")
    if mem_b:
        total, used, _ = mem_b
        pct = 0.0 if total == 0 else (used / total) * 100.0
        line_do(f"{'Memory':<7}{bar(pct)}  {pct:5.1f}% ({format_size(used)}/{format_size(total)})")
    else:
        line_skip("Memory usage unavailable")
    if disk_b:
        total, used, _ = disk_b
        pct = 0.0 if total == 0 else (used / total) * 100.0
        line_do(f"{'Disk':<7}{bar(pct)}  {pct:5.1f}% ({format_size(used)}/{format_size(total)})")
    else:
        line_skip("Disk usage unavailable")

    section("Health score")
    score = 100
    if cpu is not None:
        if cpu > 90:
            score -= 30
        elif cpu > 75:
            score -= 15
    if mem_b:
        total, used, _ = mem_b
        pct = 0.0 if total == 0 else (used / total) * 100.0
        if pct > 90:
            score -= 30
        elif pct > 80:
            score -= 15
    if disk_b:
        total, used, _ = disk_b
        pct = 0.0 if total == 0 else (used / total) * 100.0
        if pct > 90:
            score -= 30
        elif pct > 85:
            score -= 15
    score = max(0, min(100, score))
    if RICH and console is not None:
        color = "green" if score >= 80 else "yellow" if score >= 50 else "red"
        console.print(f"Health ● {score}", style=color, highlight=False)
    else:
        p(f"Health ● {score}")

    section("Disk I/O")
    with scan_status("Scanning disk I/O..."):
        io = disk_io_rate()
    if io:
        read_bps, write_bps = io
        line_do(f"Read  {format_size(int(read_bps))}/s")
        line_do(f"Write {format_size(int(write_bps))}/s")
    else:
        line_skip("Disk I/O unavailable")

    section("Network")
    with scan_status("Scanning network..."):
        net = net_io_rate()
    if net:
        rows = []
        for iface, rx, tx in net[:5]:
            rows.append([iface, f"{format_size(int(rx))}/s", f"{format_size(int(tx))}/s"])
        table("Top interfaces", ["Iface", "Down", "Up"], rows)
    else:
        line_skip("Network I/O unavailable")

    section("Disk")
    with scan_status("Scanning disk..."):
        try:
            out = subprocess.check_output(["df", "-h", "-x", "tmpfs", "-x", "devtmpfs"], text=True)
        except Exception:
            out = ""
    if out:
        p(out)
    else:
        line_warn("Could not read df -h")

    section("Inodes")
    with scan_status("Scanning inodes..."):
        try:
            out = subprocess.check_output(["df", "-i", "-x", "tmpfs", "-x", "devtmpfs"], text=True)
        except Exception:
            out = ""
    if out:
        p(out)
    else:
        line_warn("Could not read df -i")

    section("Journald")
    if which("journalctl"):
        with scan_status("Scanning journald..."):
            try:
                out = capture(["journalctl", "--disk-usage"])
            except Exception:
                out = ""
        if out:
            line_do(f"Disk usage: {out}")
        else:
            line_warn("Could not read journald usage")
    else:
        line_skip("journalctl not available")

    section("System health")
    with scan_status("Scanning failed units..."):
        failed = systemctl_failed_units()
    if failed is None:
        line_skip("systemctl not available")
    elif not failed:
        line_ok("No failed units")
    else:
        line_warn(f"Failed units: {len(failed)}")
        for unit in failed[:10]:
            line_do(unit)
        if len(failed) > 10:
            line_do(f"... and {len(failed) - 10} more")

    section("Top processes")
    cpu_top = top_processes("-%cpu", 5)
    mem_top = top_processes("-%mem", 5)
    if cpu_top:
        table("Top CPU", ["PID", "Command", "CPU%", "MEM%"], cpu_top)
    else:
        line_skip("Top CPU not available")
    if mem_top:
        table("Top Memory", ["PID", "Command", "CPU%", "MEM%"], mem_top)
    else:
        line_skip("Top memory not available")

    section("Packages")
    with scan_status("Scanning APT cache..."):
        apt_cache = du_size("/var/cache/apt/archives")
    if apt_cache:
        line_do(f"APT cache: {apt_cache}")
    else:
        line_skip("APT cache size not available")
    with scan_status("Scanning autoremove candidates..."):
        count = apt_autoremove_count()
    if count is None:
        line_skip("Autoremove count not available")
    else:
        line_do(f"Autoremove candidates: {count}")

    section("Kernel")
    with scan_status("Scanning kernels..."):
        candidates = kernel_cleanup_candidates()
    if candidates:
        line_warn(f"Old kernels detected: {len(candidates)} (clean with --kernels)")
        for pkg in candidates[:10]:
            line_do(pkg)
        if len(candidates) > 10:
            line_do(f"... and {len(candidates) - 10} more")
    else:
        line_ok("No old kernels detected")

    section("Reboot")
    if reboot_required():
        line_warn("Reboot required")
    else:
        line_ok("No reboot required")


def cmd_status_all(args: argparse.Namespace) -> None:
    cmd_status_system(args)
    if getattr(args, "paths", False):
        section("PATH audit")
        with scan_status("Scanning PATH entries..."):
            res = analyze_paths()
        line_do(f"Entries: {len(res['entries'])}")
        if res["duplicates"]:
            line_warn(f"Duplicates: {len(res['duplicates'])}")
            for pth in res["duplicates"][:10]:
                line_do(pth)
        else:
            line_ok("No duplicates")
        if res["missing"]:
            line_warn(f"Missing directories: {len(res['missing'])}")
            for pth in res["missing"][:10]:
                line_do(pth)
        else:
            line_ok("No missing directories")
        if res["rc_hits"]:
            line_do(f"RC PATH entries: {len(res['rc_hits'])}")
            for line in res["rc_hits"][:10]:
                line_do(line)
        else:
            line_ok("No PATH entries found in rc files")
    cmd_docker_status(args)
    section("Status summary")
    rows = []
    mem_b = mem_usage_bytes()
    disk_b = disk_usage_bytes("/")
    failed = systemctl_failed_units()
    autoremove = apt_autoremove_count()
    if mem_b:
        total, used, _ = mem_b
        rows.append(["Memory", f"{format_size(used)}/{format_size(total)}"])
    if disk_b:
        total, used, avail = disk_b
        rows.append(["Disk", f"{format_size(used)}/{format_size(total)} | Free {format_size(avail)}"])
    if failed is None:
        rows.append(["Failed units", "n/a"])
    else:
        rows.append(["Failed units", str(len(failed))])
    if autoremove is None:
        rows.append(["Autoremove candidates", "n/a"])
    else:
        rows.append(["Autoremove candidates", str(autoremove)])
    if reboot_required():
        rows.append(["Reboot", "Required"])
    else:
        rows.append(["Reboot", "Not required"])
    if docker_available():
        try:
            containers = docker_ps_all()
            running = [c for c in containers if (c.get("State") or "").lower() == "running"]
            images = docker_images_all()
            volumes = docker_volumes()
            rows.append(["Docker", f"{len(running)}/{len(containers)} running | {len(images)} images | {len(volumes)} volumes"])
        except Exception:
            rows.append(["Docker", "n/a"])
    if rows:
        table("Summary", ["Item", "Value"], rows)


def cmd_docker_status(args: argparse.Namespace) -> None:
    if not docker_available():
        line_warn("Docker is not installed or not accessible.")
        return
    if not is_root() and docker_logs_dir_exists() and not can_read_docker_logs():
        maybe_reexec_with_sudo("Permissions are required to read Docker logs.")

    with scan_status("Scanning Docker summary..."):
        containers = docker_ps_all()
        running = [c for c in containers if (c.get("State") or "").lower() == "running"]
        images = docker_images_all()
        volumes = docker_volumes()
    line_do(f"Docker: containers {len(running)}/{len(containers)} | images {len(images)} | volumes {len(volumes)}")

    section("Docker system df")
    with scan_status("Scanning Docker system df..."):
        try:
            out = docker_system_df()
        except Exception:
            out = ""
    if out:
        p(out)
    else:
        line_warn("Could not read docker system df")

    section("Docker builder du")
    with scan_status("Scanning Docker builder du..."):
        try:
            out = docker_builder_df()
        except Exception:
            out = ""
    if out:
        p(out)
    else:
        line_warn("Could not read docker builder du")

    section("Dangling images")
    with scan_status("Scanning images..."):
        dangling, unused = compute_unused_images()
    line_do(f"Dangling (orphaned layers): {len(dangling)}")
    line_do(f"Unused (not used by any container): {len(unused)}")
    if dangling:
        table("Dangling images (top 20)", ["ID", "Repo", "Tag", "Size", "Age"], cap_imgs(dangling, 20))
    if unused:
        table("Unused images (top 20)", ["ID", "Repo", "Tag", "Size", "Age"], cap_imgs(unused, 20))

    section("Docker logs")
    if can_read_docker_logs():
        with scan_status("Scanning Docker logs..."):
            logs = stat_logs(top_n=args.top_logs)
        if logs:
            rows = []
            for cid, lp, sz in logs:
                rows.append([cid[:12], human_bytes(sz), str(lp)])
            table(f"Docker logs (top {args.top_logs})", ["Container", "Size", "Path"], rows)
        else:
            line_ok("Nothing to show")
    else:
        line_warn("No permissions to read Docker logs")
