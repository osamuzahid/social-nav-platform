"""Source Jazzy (+ optional overlays) then exec a command."""

from __future__ import annotations

import shlex
from pathlib import Path

from social_nav_runner.layout import ros_setups

JAZZY = Path("/opt/ros/jazzy/setup.bash")


def sourced_argv(argv: list[str], extra_setups: list[Path] | None = None) -> list[str]:
    setups = [JAZZY]
    setups.extend(extra_setups if extra_setups is not None else ros_setups())
    parts = []
    for path in setups:
        if path.is_file():
            parts.append(f"source {shlex.quote(str(path))}")
    if not parts:
        return argv
    inner = " && ".join(parts + ["exec " + " ".join(shlex.quote(a) for a in argv)])
    return ["bash", "-lc", inner]
