"""Poll ROS topics, actions, lifecycle, and Isaac log markers."""

from __future__ import annotations

import re
import subprocess
import time
from pathlib import Path

from social_nav_runner.rosenv import sourced_argv


def wait_log_marker(path: Path, needle: str, timeout_s: float) -> None:
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        if path.is_file() and needle in path.read_text(errors="replace"):
            return
        time.sleep(0.5)
    raise TimeoutError(f"timed out waiting for {needle!r} in {path}")


def _run(env: dict[str, str], argv: list[str], timeout: float = 8.0) -> int:
    try:
        return subprocess.run(
            sourced_argv(argv),
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=timeout,
            check=False,
        ).returncode
    except subprocess.TimeoutExpired:
        return 1


def wait_topic(
    env: dict[str, str],
    topic: str,
    timeout_s: float,
    *,
    qos: str | None = "best_effort",
) -> None:
    deadline = time.time() + timeout_s
    extra: list[str] = []
    if qos:
        extra.extend(["--qos-reliability", qos])
    while time.time() < deadline:
        argv = ["timeout", "3", "ros2", "topic", "echo", topic, "--once", *extra]
        if _run(env, argv, timeout=6.0) == 0:
            return
        time.sleep(1.0)
    raise TimeoutError(f"no data on {topic}")


def wait_action(env: dict[str, str], name: str, timeout_s: float) -> None:
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        try:
            proc = subprocess.run(
                sourced_argv(["ros2", "action", "list"]),
                env=env,
                capture_output=True,
                text=True,
                timeout=8.0,
                check=False,
            )
        except subprocess.TimeoutExpired:
            proc = None
        if proc is not None and name in (proc.stdout or ""):
            return
        time.sleep(1.0)
    raise TimeoutError(f"action {name} not advertised")


def list_nodes(env: dict[str, str]) -> str:
    try:
        proc = subprocess.run(
            sourced_argv(["ros2", "node", "list"]),
            env=env,
            capture_output=True,
            text=True,
            timeout=8.0,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return ""
    return proc.stdout or ""


def wait_node(env: dict[str, str], name: str, timeout_s: float) -> None:
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        if name in list_nodes(env):
            return
        time.sleep(1.0)
    raise TimeoutError(f"node {name} not listed")


def lifecycle_get(env: dict[str, str], node: str) -> str:
    try:
        proc = subprocess.run(
            sourced_argv(["ros2", "lifecycle", "get", node]),
            env=env,
            capture_output=True,
            text=True,
            timeout=8.0,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return ""
    return ((proc.stdout or "") + (proc.stderr or "")).strip()


def lifecycle_is_active(text: str) -> bool:
    if "inactive" in text.lower():
        return False
    return bool(re.search(r"\bactive\b", text, re.I))


def wait_service(env: dict[str, str], name: str, timeout_s: float) -> None:
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        try:
            proc = subprocess.run(
                sourced_argv(["ros2", "service", "list"]),
                env=env,
                capture_output=True,
                text=True,
                timeout=8.0,
                check=False,
            )
        except subprocess.TimeoutExpired:
            proc = None
        if proc is not None and name in (proc.stdout or ""):
            return
        time.sleep(1.0)
    raise TimeoutError(f"service {name} not advertised")


def topic_has_data(env: dict[str, str], topic: str, qos: str | None = None) -> bool:
    extra: list[str] = []
    if qos:
        extra.extend(["--qos-reliability", qos])
    return _run(env, ["timeout", "2", "ros2", "topic", "echo", topic, "--once", *extra], timeout=5.0) == 0
