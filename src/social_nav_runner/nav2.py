"""Nav2 Smac 2D hop: standalone map_server + nav2_bringup, then NavigateToPose.

Tracked planner YAML keeps a BT XML basename so the tree is relocatable.
Nav2 opens default_nav_to_pose_bt_xml as a filesystem path (cwd or ament
share), not relative to this YAML. Bring-up writes a session copy with an
absolute path — freeze hops pin the same 20 Hz replanning tree absolutely
under tools/nav2_smoke/.

PlannerReady is bt_navigator lifecycle active. The NavigateToPose action
is advertised while the node is inactive and then rejects goals.
"""

from __future__ import annotations

import math
import os
import re
import subprocess
import time
from pathlib import Path

from social_nav_runner.errors import HopError, as_hop
from social_nav_runner.experiments import Experiment
from social_nav_runner.layout import Layout
from social_nav_runner.processes import ProcessGroup
from social_nav_runner.rosenv import sourced_argv
from social_nav_runner.waiters import lifecycle_get, lifecycle_is_active, list_nodes, wait_action

NAV2_BT_XML_NAME = "navigate_to_pose_w_replanning_20hz.xml"
_BT_XML_LINE = re.compile(
    r'(default_nav_to_pose_bt_xml:\s*)["\']?[^"\'\n]+["\']?'
)
_BRINGUP_FAILURES = (
    "Couldn't open input XML file",
    "Aborting bringup",
    "Failed to change state for node: bt_navigator",
)


def _yaw_quat(yaw: float) -> tuple[float, float]:
    return math.sin(yaw / 2.0), math.cos(yaw / 2.0)


def materialize_nav2_params(layout: Layout, robot: str, dest: Path) -> Path:
    src = layout.nav2_params(robot)
    bt = layout.nav2_bt_xml()
    if not src.is_file():
        raise HopError("configuration_error", f"missing {src}")
    if not bt.is_file():
        raise HopError("configuration_error", f"missing Nav2 BT XML {bt}")
    text = src.read_text(encoding="utf-8")
    new, n = _BT_XML_LINE.subn(rf'\1"{bt}"', text, count=1)
    if n != 1:
        raise HopError("configuration_error", f"{src} missing default_nav_to_pose_bt_xml")
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(new, encoding="utf-8")
    return dest


def nav2_bringup_failure(log_text: str) -> str | None:
    for needle in _BRINGUP_FAILURES:
        if needle in log_text:
            return needle
    return None


def bt_navigator_listed(node_list: str) -> bool:
    names = {ln.strip() for ln in node_list.splitlines() if ln.strip()}
    return "/bt_navigator" in names or "bt_navigator" in names


def bt_navigator_proc_alive() -> bool:
    proc = Path("/proc")
    if not proc.is_dir():
        return False
    for p in proc.iterdir():
        if not p.name.isdigit():
            continue
        try:
            exe = os.readlink(p / "exe")
        except OSError:
            continue
        if exe.endswith("nav2_bt_navigator/bt_navigator"):
            return True
    return False


def nav2_goal_verdict(text: str, goal_rc: int) -> str:
    if "SUCCEEDED" in text:
        return "GOAL=SUCCEEDED"
    if "ABORTED" in text:
        return "GOAL=ABORTED"
    if "CANCELED" in text or "CANCELLED" in text:
        return "GOAL=CANCELED"
    if "rejected" in text.lower() or "Rejecting the goal" in text:
        return "GOAL=REJECTED"
    if goal_rc != 0:
        return "GOAL=TIMEOUT"
    return "GOAL=UNKNOWN"


def start_nav2(
    pg: ProcessGroup,
    layout: Layout,
    exp: Experiment,
    session: Path,
    env: dict[str, str],
) -> None:
    params = materialize_nav2_params(layout, exp.robot, session / "nav2_params.yaml")
    map_yaml = layout.occupancy_yaml(exp.world)
    pg.start(
        sourced_argv(
            [
                "ros2",
                "run",
                "nav2_map_server",
                "map_server",
                "--ros-args",
                "-p",
                f"yaml_filename:={map_yaml}",
                "-p",
                "use_sim_time:=true",
                "-p",
                "frame_id:=map",
            ]
        ),
        env=env,
        log_path=session / "map_server.log",
    )
    pg.start(
        sourced_argv(
            [
                "ros2",
                "run",
                "nav2_util",
                "lifecycle_bringup",
                "map_server",
            ]
        ),
        env=env,
        log_path=session / "map_server_lifecycle.log",
    )
    pg.start(
        sourced_argv(
            [
                "ros2",
                "launch",
                "nav2_bringup",
                "bringup_launch.py",
                "use_sim_time:=True",
                f"map:={map_yaml}",
                f"params_file:={params}",
                "autostart:=True",
                "use_composition:=False",
                "use_localization:=False",
                "slam:=False",
            ]
        ),
        env=env,
        log_path=session / "nav2_bringup.log",
    )


def wait_nav2_ready(env: dict[str, str], session: Path, timeout_s: float = 180.0) -> None:
    log = session / "nav2_bringup.log"
    deadline = time.time() + timeout_s
    saw_bt = False
    saw_proc = False
    while time.time() < deadline:
        text = log.read_text(errors="replace") if log.is_file() else ""
        fail = nav2_bringup_failure(text)
        if fail:
            raise HopError("planner_startup_error", fail)
        alive = bt_navigator_proc_alive()
        if alive:
            saw_proc = True
        elif saw_proc:
            raise HopError("planner_startup_error", "bt_navigator process disappeared")
        listed = list_nodes(env)
        if bt_navigator_listed(listed):
            saw_bt = True
        elif saw_bt and listed.strip():
            raise HopError("planner_startup_error", "bt_navigator node disappeared")
        if bt_navigator_listed(listed) and lifecycle_is_active(
            lifecycle_get(env, "/bt_navigator")
        ):
            remain = max(5.0, deadline - time.time())
            as_hop("planner_startup_error", wait_action, env, "navigate_to_pose", remain)
            return
        time.sleep(0.4)
    raise HopError("planner_startup_error", "Nav2 bt_navigator did not become active")


def bringup_nav2(
    pg: ProcessGroup,
    layout: Layout,
    exp: Experiment,
    session: Path,
    env: dict[str, str],
    timeout_s: float,
) -> None:
    start_nav2(pg, layout, exp, session, env)
    wait_nav2_ready(env, session, timeout_s)


def send_nav2_goal(
    pg: ProcessGroup,
    exp: Experiment,
    session: Path,
    env: dict[str, str],
    timeout_s: float,
) -> int:
    qz, qw = _yaw_quat(float(exp.goal["yaw"]))
    pose = (
        "{pose: {header: {frame_id: 'map'}, pose: {position: {x: %s, y: %s, z: 0.0}, "
        "orientation: {x: 0.0, y: 0.0, z: %.6f, w: %.6f}}}}"
        % (exp.goal["x"], exp.goal["y"], qz, qw)
    )
    proc = pg.start(
        sourced_argv(
            [
                "timeout",
                str(int(timeout_s)),
                "ros2",
                "action",
                "send_goal",
                "/navigate_to_pose",
                "nav2_msgs/action/NavigateToPose",
                pose,
            ]
        ),
        env=env,
        log_path=session / "nav_goal.txt",
    )
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        if not bt_navigator_proc_alive():
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
            raise HopError("planner_startup_error", "bt_navigator process disappeared")
        try:
            return int(proc.wait(timeout=1.0))
        except subprocess.TimeoutExpired:
            continue
    proc.terminate()
    try:
        return int(proc.wait(timeout=5))
    except subprocess.TimeoutExpired:
        proc.kill()
        return 1
