#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Clean command implementations for LinuxMole.
"""

from __future__ import annotations
import argparse
from pathlib import Path
from typing import List, Dict

from linuxmole.output import (
    section,
    p,
    line_do,
    line_ok,
    line_skip,
    line_warn,
    table,
    scan_status,
)
from linuxmole.helpers import (
    which,
    run,
    capture,
    confirm,
    is_root,
    human_bytes,
    format_size,
    maybe_reexec_with_sudo,
)
from linuxmole.config import load_whitelist, is_whitelisted, load_config
from linuxmole.plans import Action, show_plan, exec_actions
from linuxmole.system.paths import du_bytes, find_log_candidates
from linuxmole.system.apt import kernel_cleanup_candidates, kernel_pkg_size_bytes
from linuxmole.docker.inspect import (
    docker_available,
    docker_cmd,
    docker_stopped_containers,
    docker_networks_dangling,
    docker_volumes_dangling,
    docker_volume_mountpoints,
    docker_system_df,
    docker_builder_df,
    compute_unused_images,
    cap_containers,
    cap_networks,
    cap_imgs,
)
from linuxmole.docker.logs import (
    docker_logs_dir_exists,
    can_read_docker_logs,
    docker_container_log_paths,
    stat_logs,
    total_logs_size,
    list_all_logs,
    truncate_file,
)
from linuxmole.docker.formatting import (
    sum_image_sizes,
    sum_container_sizes,
    parse_journal_usage_bytes,
)
from linuxmole.commands._helpers import (
    add_summary,
    render_summary,
    render_risks,
    summary_totals,
    write_detail_list,
    print_final_summary,
)


def apply_default_clean_flags(args: argparse.Namespace, mode: str) -> None:
    """Apply default clean flags when no specific flags are provided."""
    docker_none = not any([
        args.containers,
        args.networks,
        args.volumes,
        args.builder,
        args.system_prune,
        args.truncate_logs_mb
    ]) and args.images == "off"

    system_none = not any([
        args.journal,
        args.tmpfiles,
        args.apt,
        args.logs,
        args.pip_cache,
        args.npm_cache,
        args.cargo_cache,
        args.go_cache,
        args.snap,
        args.flatpak,
        args.logrotate
    ])

    if mode in ("all", "docker") and docker_none:
        args.containers = True
        args.networks = True
        args.images = "dangling"
        args.builder = True

    if mode in ("all", "system") and system_none:
        args.journal = True
        args.tmpfiles = True
        args.apt = True
        args.logs = True
        args.kernels = False
        args.pip_cache = True
        args.npm_cache = True
        args.cargo_cache = True
        args.go_cache = True
        args.snap = True
        args.flatpak = True


def cmd_docker_clean(args: argparse.Namespace) -> None:
    """Clean Docker resources (containers, images, volumes, logs)."""
    apply_default_clean_flags(args, "docker")

    # Load config and apply auto_confirm if needed
    config = load_config()
    clean_config = config.get("clean", {})
    if not args.yes and clean_config.get("auto_confirm", False):
        args.yes = True

    if not docker_available():
        p("Docker is not installed or not accessible.")
        return

    if not any([
        args.containers,
        args.networks,
        args.volumes,
        args.builder,
        args.system_prune,
        args.truncate_logs_mb
    ]) and args.images == "off":
        line_warn("No Docker actions selected. Use --help for options.")
        return

    section("Docker clean")
    if args.dry_run:
        line_do("Dry Run Mode - Preview only, no deletions")

    if (args.truncate_logs_mb is not None and not is_root() and
        docker_logs_dir_exists() and not can_read_docker_logs()):
        maybe_reexec_with_sudo("Permissions are required to truncate Docker logs.")

    actions: List[Action] = []

    # 1) stopped containers
    if args.containers:
        actions.append(Action(
            "Remove stopped containers",
            docker_cmd(["container", "prune", "-f"]),
            root=False
        ))

    # 2) networks
    if args.networks:
        actions.append(Action(
            "Remove dangling networks (not used)",
            docker_cmd(["network", "prune", "-f"]),
            root=False
        ))

    # 3) images
    if args.images in ("dangling", "unused", "all"):
        if args.images == "dangling":
            actions.append(Action(
                "Remove dangling images",
                docker_cmd(["image", "prune", "-f"]),
                root=False
            ))
        elif args.images == "unused":
            actions.append(Action(
                "Remove unused images (not referenced by containers)",
                docker_cmd(["image", "prune", "-a", "-f"]),
                root=False
            ))
        else:
            actions.append(Action(
                "Remove unused images (includes dangling and unreferenced)",
                docker_cmd(["image", "prune", "-a", "-f"]),
                root=False
            ))

    # 4) volumes
    if args.volumes:
        actions.append(Action(
            "Remove dangling volumes (not used)",
            docker_cmd(["volume", "prune", "-f"]),
            root=False
        ))

    # 5) builder cache
    if args.builder:
        cmd = ["builder", "prune", "-f"]
        if args.builder_all:
            cmd.append("--all")
        actions.append(Action("Clean builder cache", docker_cmd(cmd), root=False))

    # 6) system prune
    if args.system_prune:
        cmd = ["system", "prune", "-f"]
        if args.system_prune_all:
            cmd.append("-a")
        if args.system_prune_volumes:
            cmd.append("--volumes")
        actions.append(Action(
            "Docker system prune (selected flags)",
            docker_cmd(cmd),
            root=False
        ))

    # 7) logs truncation
    do_truncate = args.truncate_logs_mb is not None

    if not actions and not do_truncate:
        line_warn("No actions selected. Use --help for options.")
        return

    if actions:
        section("Plan")
        show_plan(actions, "Docker Plan")

    detail_lines: List[str] = []
    summary_items: List[Dict] = []

    section("Preview")

    if args.containers:
        with scan_status("Scanning stopped containers..."):
            stopped = docker_stopped_containers()
        size_b, unknown = sum_container_sizes(stopped)
        line_do(f"Stopped containers: {len(stopped)} ({format_size(size_b, unknown)} reported by Docker)")
        add_summary(
            summary_items,
            "Stopped containers",
            len(stopped),
            size_b,
            "reported by Docker",
            size_unknown=unknown,
            risk="low"
        )
        for it in stopped:
            detail_lines.append(f"container\t{it.get('ID','')}\t{it.get('Names','')}\t{it.get('Status','')}\t{it.get('Size','')}")
        if stopped:
            table(
                "Candidates: stopped containers (top 20)",
                ["ID", "Name", "Status", "Size"],
                cap_containers(stopped, 20)
            )
        else:
            line_ok("Nothing to clean")

    if args.networks:
        with scan_status("Scanning dangling networks..."):
            nets = docker_networks_dangling()
        line_do(f"Dangling networks: {len(nets)}")
        add_summary(summary_items, "Dangling networks", len(nets), None, risk="low")
        for it in nets:
            detail_lines.append(f"network\t{it.get('ID','')}\t{it.get('Name','')}\t{it.get('Driver','')}")
        if nets:
            table(
                "Candidates: dangling networks (top 20)",
                ["ID", "Name", "Driver"],
                cap_networks(nets, 20)
            )
        else:
            line_ok("Nothing to clean")

    if args.volumes:
        with scan_status("Scanning dangling volumes..."):
            vols = docker_volumes_dangling()
        size_b = 0
        unknown = 0
        rows = []
        if vols:
            names = [v.get("Name") or "" for v in vols if v.get("Name")]
            mountpoints = docker_volume_mountpoints(names)
            for name in names:
                mp = mountpoints.get(name)
                if not mp:
                    unknown += 1
                    continue
                b = du_bytes(mp)
                if b is None:
                    unknown += 1
                else:
                    size_b += b
            for v in vols[:20]:
                name = v.get("Name") or ""
                mp = mountpoints.get(name, "")
                rows.append([name, (v.get("Driver") or ""), mp])
                detail_lines.append(f"volume\t{name}\t{mp}")
        line_do(f"Dangling volumes: {len(vols)} ({format_size(size_b, unknown)})")
        add_summary(
            summary_items,
            "Dangling volumes",
            len(vols),
            size_b,
            size_unknown=unknown > 0,
            risk="high"
        )
        if rows:
            table(
                "Candidates: dangling volumes (top 20)",
                ["Name", "Driver", "Mountpoint"],
                rows
            )
        else:
            line_ok("Nothing to clean")

    if args.images in ("dangling", "unused", "all"):
        with scan_status("Scanning images..."):
            dangling, unused = compute_unused_images()
        if args.images == "dangling":
            size_b = sum_image_sizes(dangling)
            line_do(f"Dangling images: {len(dangling)} ({format_size(size_b)})")
            add_summary(summary_items, "Dangling images", len(dangling), size_b, risk="low")
            for it in dangling:
                detail_lines.append(f"image\t{it.get('ID','')}\t{it.get('Repository','')}:{it.get('Tag','')}\t{it.get('Size','')}")
            if dangling:
                table(
                    "Candidates: dangling images (top 20)",
                    ["ID", "Repo", "Tag", "Size", "Age"],
                    cap_imgs(dangling, 20)
                )
            else:
                line_ok("Nothing to clean")
        else:
            size_b = sum_image_sizes(dangling) + sum_image_sizes(unused)
            line_do(f"Unused images: {len(dangling) + len(unused)} ({format_size(size_b)})")
            add_summary(
                summary_items,
                "Unused images",
                len(dangling) + len(unused),
                size_b,
                risk="med"
            )
            for it in dangling + unused:
                detail_lines.append(f"image\t{it.get('ID','')}\t{it.get('Repository','')}:{it.get('Tag','')}\t{it.get('Size','')}")
            if dangling:
                table(
                    "Candidates: dangling images (top 20)",
                    ["ID", "Repo", "Tag", "Size", "Age"],
                    cap_imgs(dangling, 20)
                )
            if unused:
                table(
                    "Candidates: unused images (top 20)",
                    ["ID", "Repo", "Tag", "Size", "Age"],
                    cap_imgs(unused, 20)
                )
            if not dangling and not unused:
                line_ok("Nothing to clean")

    if args.builder:
        line_do("Builder cache: inspection available via docker builder du")
        add_summary(summary_items, "Builder cache", 0, None, risk="low")
        with scan_status("Scanning Docker builder du..."):
            try:
                out = docker_builder_df()
            except Exception:
                out = ""
        if out:
            p(out)

    if args.system_prune:
        line_do("Docker system prune: inspection available via docker system df")
        add_summary(summary_items, "Docker system prune", 0, None, risk="high")
        with scan_status("Scanning Docker system df..."):
            try:
                out = docker_system_df()
            except Exception:
                out = ""
        if out:
            p(out)

    if do_truncate:
        threshold_bytes = int(args.truncate_logs_mb * 1024 * 1024)
        with scan_status("Scanning Docker logs..."):
            logs = stat_logs(top_n=500)
        to_trunc = [(cid, lp, sz) for (cid, lp, sz) in logs if sz >= threshold_bytes]
        rows = [[cid[:12], human_bytes(sz), str(lp)] for (cid, lp, sz) in to_trunc[:50]]
        if rows:
            table(
                f"Logs to truncate (>= {args.truncate_logs_mb}MB) [showing up to 50]",
                ["Container", "Size", "Path"],
                rows
            )
            total_logs = sum(sz for _, _, sz in to_trunc)
            add_summary(
                summary_items,
                "Docker logs (json-file)",
                len(to_trunc),
                total_logs,
                risk="med"
            )
            for _, lp, sz in to_trunc:
                detail_lines.append(f"log\t{lp}\t{sz}")
        else:
            line_ok(f"No logs >= {args.truncate_logs_mb}MB")
            add_summary(summary_items, "Docker logs (json-file)", 0, 0, risk="med")
    else:
        if can_read_docker_logs():
            with scan_status("Scanning Docker logs..."):
                logs = stat_logs(top_n=20)
            if logs:
                rows = [[cid[:12], human_bytes(sz), str(lp)] for (cid, lp, sz) in logs]
                table("Current logs (top 20)", ["Container", "Size", "Path"], rows)
            total_b, total_count = total_logs_size()
            add_summary(
                summary_items,
                "Docker logs (json-file)",
                total_count,
                total_b,
                risk="med"
            )
            for _, lp, sz in list_all_logs():
                detail_lines.append(f"log\t{lp}\t{sz}")
        else:
            line_warn("No permissions to read Docker logs")
            add_summary(
                summary_items,
                "Docker logs (json-file)",
                0,
                None,
                count_display="-",
                risk="med"
            )

    if summary_items:
        section("Summary")
        render_summary(summary_items)
        section("Risk levels")
        render_risks(summary_items)
    else:
        line_warn("Summary: no actions selected.")

    total_bytes, unknown, total_items, categories = summary_totals(summary_items)
    log_path = write_detail_list(detail_lines, "clean-list.txt")

    if args.dry_run:
        print_final_summary(True, total_bytes, unknown, total_items, categories, log_path)
        return

    if not confirm("Run the plan?", args.yes):
        p("Cancelled.")
        return

    if actions:
        exec_actions(actions, dry_run=args.dry_run)

    if do_truncate:
        threshold_bytes = int(args.truncate_logs_mb * 1024 * 1024)
        all_logs = []
        for cid, lp in docker_container_log_paths():
            try:
                sz = lp.stat().st_size
                if sz >= threshold_bytes:
                    all_logs.append((cid, lp, sz))
            except Exception:
                pass
        all_logs.sort(key=lambda x: x[2], reverse=True)
        for cid, lp, sz in all_logs:
            p(f"[log] truncate {cid[:12]} {human_bytes(sz)} {lp}")
            truncate_file(lp, dry_run=args.dry_run)

    print_final_summary(False, total_bytes, unknown, total_items, categories, log_path)


def cmd_clean_system(args: argparse.Namespace) -> None:
    """Clean system resources (journal, tmp, apt, logs, kernels, caches)."""
    apply_default_clean_flags(args, "system")

    # Load config and apply defaults
    config = load_config()
    clean_config = config.get("clean", {})

    # Apply config defaults when CLI args are None
    if args.journal_time is None:
        args.journal_time = clean_config.get("default_journal_time", "3d")
    if args.journal_size is None:
        args.journal_size = clean_config.get("default_journal_size", "500M")
    if args.logs_days is None:
        args.logs_days = clean_config.get("preserve_recent_days", 7)

    # Apply auto_confirm from config if not explicitly set via CLI
    if not args.yes and clean_config.get("auto_confirm", False):
        args.yes = True

    section("Clean system")
    if args.dry_run:
        line_do("Dry Run Mode - Preview only, no deletions")

    if (args.journal or args.tmpfiles or args.apt) and not is_root():
        maybe_reexec_with_sudo("Root permissions are required for clean system.")

    actions: List[Action] = []

    # journald
    if args.journal and which("journalctl"):
        if args.journal_time:
            actions.append(Action(
                f"Journald vacuum by time (keep {args.journal_time})",
                ["journalctl", f"--vacuum-time={args.journal_time}"],
                root=True
            ))
        if args.journal_size:
            actions.append(Action(
                f"Journald vacuum by size (cap {args.journal_size})",
                ["journalctl", f"--vacuum-size={args.journal_size}"],
                root=True
            ))

    # tmpfiles
    if args.tmpfiles and which("systemd-tmpfiles"):
        actions.append(Action(
            "systemd-tmpfiles --clean",
            ["systemd-tmpfiles", "--clean"],
            root=True
        ))

    # apt
    if args.apt and which("apt-get"):
        actions.append(Action("apt autoremove", ["apt-get", "-y", "autoremove"], root=True))
        actions.append(Action("apt autoclean", ["apt-get", "-y", "autoclean"], root=True))
        actions.append(Action("apt clean", ["apt-get", "clean"], root=True))

    # logs
    if args.logs:
        actions.append(Action(
            f"Clean rotated logs older than {args.logs_days}d",
            ["true"],
            root=True
        ))

    if args.kernels:
        actions.append(Action(
            f"Remove old kernels (keep {args.kernels_keep})",
            ["true"],
            root=True
        ))

    if args.pip_cache:
        actions.append(Action("Clean pip cache", ["true"], root=True))
    if args.npm_cache:
        actions.append(Action("Clean npm cache", ["true"], root=True))
    if args.cargo_cache:
        actions.append(Action("Clean cargo cache", ["true"], root=True))
    if args.go_cache:
        actions.append(Action("Clean Go module cache", ["true"], root=True))
    if args.snap:
        actions.append(Action("Clean old snap revisions", ["true"], root=True))
    if args.flatpak:
        actions.append(Action("Clean unused flatpak runtimes", ["true"], root=True))
    if args.logrotate:
        actions.append(Action(
            "Force logrotate",
            ["logrotate", "-f", "/etc/logrotate.conf"],
            root=True
        ))

    if not actions:
        line_warn("Nothing to do (or tools not available).")
        return

    section("Plan")
    show_plan(actions, "System Plan")

    detail_lines: List[str] = []
    summary_items: List[Dict] = []

    section("Preview")

    if args.journal and which("journalctl"):
        with scan_status("Scanning journald..."):
            try:
                usage = capture(["journalctl", "--disk-usage"])
            except Exception:
                usage = ""
        if usage:
            line_do(f"Journald: {usage}")
            size_b = parse_journal_usage_bytes(usage)
            add_summary(summary_items, "Journald", 1, size_b, risk="med")
            detail_lines.append("journald\tjournalctl --disk-usage")
        else:
            line_warn("Could not read journald usage")

    if args.tmpfiles:
        with scan_status("Scanning /tmp and /var/tmp..."):
            tmp_b = du_bytes("/tmp")
            var_tmp_b = du_bytes("/var/tmp")
        tmp_info = f"/tmp: {format_size(tmp_b)} | /var/tmp: {format_size(var_tmp_b)}"
        line_do(f"Tmpfiles: {tmp_info}")
        total_tmp = (tmp_b or 0) + (var_tmp_b or 0)
        unknown = tmp_b is None or var_tmp_b is None
        add_summary(
            summary_items,
            "Tmpfiles",
            2,
            total_tmp,
            size_unknown=unknown,
            risk="low"
        )
        detail_lines.append("tmpfiles\t/tmp")
        detail_lines.append("tmpfiles\t/var/tmp")

    if args.apt:
        with scan_status("Scanning APT cache..."):
            apt_b = du_bytes("/var/cache/apt/archives")
        line_do(f"APT cache: {format_size(apt_b)}")
        add_summary(summary_items, "APT cache", 1, apt_b, risk="low")
        detail_lines.append("apt\t/var/cache/apt/archives")

    if args.logs:
        with scan_status("Scanning rotated logs..."):
            logs = find_log_candidates(args.logs_days)
        total_logs = sum(sz for _, sz in logs)
        add_summary(summary_items, "Rotated logs", len(logs), total_logs, risk="med")
        if logs:
            for path, sz in logs[:50]:
                detail_lines.append(f"log\t{path}\t{sz}")
            rows = [[Path(p).name, human_bytes(sz), p] for p, sz in logs[:20]]
            table("Rotated logs (top 20)", ["File", "Size", "Path"], rows)
            line_do(f"Rotated logs: {len(logs)} ({format_size(total_logs)})")
        else:
            line_ok("No rotated logs to clean")

    if args.kernels:
        with scan_status("Scanning old kernels..."):
            candidates = kernel_cleanup_candidates(args.kernels_keep)
        size_b = kernel_pkg_size_bytes(candidates)
        add_summary(summary_items, "Old kernels", len(candidates), size_b, risk="high")
        if candidates:
            rows = [[pkg, "", ""] for pkg in candidates[:20]]
            table("Kernel packages to remove (top 20)", ["Package", "Version", "Note"], rows)
            line_do(f"Old kernels: {len(candidates)} ({format_size(size_b)})")
            for pkg in candidates:
                detail_lines.append(f"kernel\t{pkg}")
        else:
            line_ok("No old kernels to clean")

    patterns = load_whitelist()

    def _cache_preview(label: str, path: Path, flag: bool) -> None:
        if not flag:
            return
        if not path.exists():
            line_skip(f"{label}: not found")
            add_summary(summary_items, label, 0, 0, risk="low")
            return
        pstr = str(path)
        if is_whitelisted(pstr, patterns):
            line_skip(f"{label}: whitelisted")
            add_summary(summary_items, label, 0, 0)
            return
        size_b = du_bytes(pstr)
        add_summary(summary_items, label, 1, size_b, risk="low")
        line_do(f"{label}: {format_size(size_b)}")
        detail_lines.append(f"cache\t{pstr}")

    _cache_preview("pip cache", Path("~/.cache/pip").expanduser(), args.pip_cache)
    _cache_preview("npm cache", Path("~/.npm").expanduser(), args.npm_cache)
    _cache_preview("cargo cache", Path("~/.cargo/registry").expanduser(), args.cargo_cache)
    _cache_preview("cargo git", Path("~/.cargo/git").expanduser(), args.cargo_cache)
    _cache_preview("go module cache", Path("~/go/pkg/mod").expanduser(), args.go_cache)

    if args.snap:
        with scan_status("Scanning snap revisions..."):
            candidates = []
            if which("snap"):
                try:
                    out = capture(["snap", "list", "--all"])
                    for line in out.splitlines()[1:]:
                        parts = line.split()
                        if len(parts) >= 6 and parts[5] == "disabled":
                            candidates.append((parts[0], parts[2]))
                except Exception:
                    candidates = []
        add_summary(summary_items, "snap revisions", len(candidates), None, risk="med")
        if candidates:
            rows = [[n, r] for n, r in candidates[:20]]
            table("Snap revisions to remove (top 20)", ["Name", "Rev"], rows)
        else:
            line_ok("No old snap revisions")

    if args.flatpak:
        line_do("Flatpak: will run flatpak uninstall --unused")
        add_summary(summary_items, "flatpak unused", 0, None, risk="med")

    if summary_items:
        section("Summary")
        render_summary(summary_items)
        section("Risk levels")
        render_risks(summary_items)
    else:
        line_warn("Summary: no actions selected.")

    total_bytes, unknown, total_items, categories = summary_totals(summary_items)
    log_path = write_detail_list(detail_lines, "clean-list.txt")

    if args.dry_run:
        print_final_summary(True, total_bytes, unknown, total_items, categories, log_path)
        return

    if not confirm("Run the plan?", args.yes):
        p("Cancelled.")
        return

    patterns = load_whitelist()
    if args.logs:
        logs = find_log_candidates(args.logs_days)
        for path, _ in logs:
            if is_whitelisted(path, patterns):
                continue
            run(["rm", "-f", path], dry_run=args.dry_run, check=False)

    if args.kernels:
        candidates = kernel_cleanup_candidates(args.kernels_keep)
        if candidates:
            run(["apt-get", "-y", "purge", *candidates], dry_run=args.dry_run, check=False)

    def _rm_cache(path: Path, flag: bool) -> None:
        if not flag:
            return
        pstr = str(path)
        if is_whitelisted(pstr, patterns):
            return
        if path.exists():
            run(["rm", "-rf", pstr], dry_run=args.dry_run, check=False)

    _rm_cache(Path("~/.cache/pip").expanduser(), args.pip_cache)
    _rm_cache(Path("~/.npm").expanduser(), args.npm_cache)
    _rm_cache(Path("~/.cargo/registry").expanduser(), args.cargo_cache)
    _rm_cache(Path("~/.cargo/git").expanduser(), args.cargo_cache)
    _rm_cache(Path("~/go/pkg/mod").expanduser(), args.go_cache)

    if args.snap and which("snap"):
        try:
            out = capture(["snap", "list", "--all"])
            for line in out.splitlines()[1:]:
                parts = line.split()
                if len(parts) >= 6 and parts[5] == "disabled":
                    run(
                        ["snap", "remove", parts[0], "--revision", parts[2]],
                        dry_run=args.dry_run,
                        check=False
                    )
        except Exception:
            pass

    if args.flatpak and which("flatpak"):
        run(["flatpak", "uninstall", "-y", "--unused"], dry_run=args.dry_run, check=False)

    exec_actions(actions, dry_run=args.dry_run)
    print_final_summary(False, total_bytes, unknown, total_items, categories, log_path)


def cmd_clean_all(args: argparse.Namespace) -> None:
    """Clean all: system + docker."""
    apply_default_clean_flags(args, "all")
    line_do("Full clean: system + docker")
    cmd_clean_system(args)
    cmd_docker_clean(args)
