#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Action planning and execution for LinuxMole.
"""

from __future__ import annotations
import shlex
from dataclasses import dataclass
from typing import List

from linuxmole.helpers import run, is_root, which
from linuxmole.output import table, p


@dataclass
class Action:
    """Represents an action to be executed."""
    label: str
    cmd: List[str]
    root: bool = False


def show_plan(actions: List[Action], heading: str) -> None:
    """Display a plan of actions to be executed."""
    rows = []
    for i, a in enumerate(actions, 1):
        rows.append([str(i), a.label + (" (root)" if a.root else ""), " ".join(shlex.quote(x) for x in a.cmd)])
    table(heading, ["#", "Action", "Command"], rows)


def exec_actions(actions: List[Action], dry_run: bool) -> None:
    """Execute a list of actions."""
    for a in actions:
        if a.root and not is_root():
            if which("sudo"):
                run(["sudo", *a.cmd], dry_run=dry_run, check=False)
            else:
                p(f"[skip] requires root and sudo is not available: {a.label}")
        else:
            run(a.cmd, dry_run=dry_run, check=False)
