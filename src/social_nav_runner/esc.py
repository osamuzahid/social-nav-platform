"""ESC hop: freeze run_esc_isaac.sh sequence on Isaac domain 0 (no Nav2).

Relays first so /odom_esc is RELIABLE (Isaac /odom is BEST_EFFORT). Mapper
starts after that odom. Planner starts after /get_grid_map. Goals wait until
the planner log shows setup() finished — the node exists during construction
and drops volatile query_goal. Then a short laser settle so live /scan marks
props before the first RRT* query.
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any

from social_nav_runner.errors import as_hop
from social_nav_runner.experiments import Experiment
from social_nav_runner.layout import Layout
from social_nav_runner.processes import ProcessGroup
from social_nav_runner.rosenv import sourced_argv
from social_nav_runner.waiters import wait_log_marker, wait_node, wait_service, wait_topic

ESC_LASER_SETTLE_S = 4.0


def planning_bounds_argv(spec: dict[str, Any]) -> list[str]:
    extra: list[str] = []
    for key, param in (
        ("esc_bounds_x", "planning_bounds_x"),
        ("esc_bounds_y", "planning_bounds_y"),
    ):
        rendered = _ros_bounds(spec.get(key))
        if rendered:
            extra.extend(["-p", f"{param}:={rendered}"])
    return extra


def _ros_bounds(values: Any) -> str | None:
    if not values:
        return None
    if isinstance(values, str):
        inner = values.strip().strip("[]")
        return f"[{inner}]" if inner else None
    return "[" + ",".join(str(float(v)) for v in values) + "]"


def esc_goal_verdict(text: str, goal_rc: int) -> str:
    if "GOAL=SUCCEEDED" in text:
        return "GOAL=SUCCEEDED"
    if "GOAL=TIMEOUT" in text:
        return "GOAL=TIMEOUT"
    if goal_rc != 0:
        return "GOAL=FAILED"
    return "GOAL=UNKNOWN"


def _py(env: dict[str, str]) -> str:
    return env.get("AMENT_PYTHON_EXECUTABLE", "/usr/bin/python3")


def bringup_esc(
    pg: ProcessGroup,
    layout: Layout,
    exp: Experiment,
    session: Path,
    env: dict[str, str],
    timeout_s: float,
) -> None:
    adapter = layout.platform / "src" / "social_nav_esc_adapter"
    params = layout.esc_params(exp.robot)
    laser = layout.laser_frame(exp.robot)
    octo = layout.octomap_bt(exp.world)
    py = _py(env)

    pg.start(
        sourced_argv(
            [
                py,
                str(adapter / "qos_relay.py"),
                "--in-topic",
                "/odom",
                "--out-topic",
                "/odom_esc",
                "--type",
                "nav_msgs/msg/Odometry",
                "--node-name",
                "esc_qos_relay_odom",
            ]
        ),
        env=env,
        log_path=session / "relay_odom.log",
    )
    pg.start(
        sourced_argv(
            [
                py,
                str(adapter / "qos_relay.py"),
                "--in-topic",
                "/scan",
                "--out-topic",
                "/scan_esc",
                "--type",
                "sensor_msgs/msg/LaserScan",
                "--node-name",
                "esc_qos_relay_scan",
            ]
        ),
        env=env,
        log_path=session / "relay_scan.log",
    )
    pg.start(
        sourced_argv(
            [
                py,
                str(adapter / "hunav_to_pedsim.py"),
                "--ros-args",
                "-p",
                "use_sim_time:=true",
            ]
        ),
        env=env,
        log_path=session / "hunav_to_pedsim.log",
    )
    as_hop("ros_readiness_error", wait_topic, env, "/odom_esc", timeout_s, qos="reliable")

    pg.start(
        sourced_argv(
            [
                "ros2",
                "run",
                "esc_move_base_control",
                "base_controller",
                "--ros-args",
                "--params-file",
                str(params),
                "-p",
                "use_sim_time:=true",
            ]
        ),
        env=env,
        log_path=session / "control.log",
    )
    mapper = [
        "ros2",
        "run",
        "esc_move_base_mapping",
        "esc_move_base_mapper",
        "--ros-args",
        "--params-file",
        str(params),
        "-p",
        "odometry_topic:=/odom_esc",
        "-p",
        "robot_frame:=base_link",
        "-p",
        f"point_cloud_frame:={laser}",
        "-p",
        f"laser_scan_frame:={laser}",
        "-p",
        "laser_scan_topic:=/scan_esc",
        "-p",
        f"offline_octomap_path:={octo}",
        "-p",
        "rviz_timer:=1.0",
    ]
    pg.start(sourced_argv(mapper), env=env, log_path=session / "mapper.log")
    as_hop("planner_startup_error", wait_service, env, "get_grid_map", timeout_s)

    spec = layout.world_spec(exp.world)
    planner = [
        "ros2",
        "run",
        "esc_move_base_planning",
        "esc_move_base_planner",
        "--ros-args",
        "--params-file",
        str(params),
        "-p",
        "odometry_topic:=/odom_esc",
        "-p",
        "solution_path_topic:=/esc_move_base_planner/esc_move_base_solution_path",
        "-p",
        "grid_map_service:=/get_grid_map",
        "-p",
        "query_goal_topic:=/esc_move_base_planner/query_goal",
        "-p",
        "use_sim_time:=true",
        *planning_bounds_argv(spec),
    ]
    pg.start(sourced_argv(planner), env=env, log_path=session / "planner.log")
    as_hop("planner_startup_error", wait_node, env, "online_planning_framework", timeout_s)
    as_hop(
        "planner_startup_error",
        wait_log_marker,
        session / "planner.log",
        "Planner range detected",
        timeout_s,
    )
    time.sleep(ESC_LASER_SETTLE_S)


def send_esc_goal(
    pg: ProcessGroup,
    layout: Layout,
    exp: Experiment,
    session: Path,
    env: dict[str, str],
    timeout_s: float,
) -> int:
    adapter = layout.platform / "src" / "social_nav_esc_adapter"
    proc = pg.start(
        sourced_argv(
            [
                _py(env),
                str(adapter / "send_esc_goal.py"),
                "--x",
                str(exp.goal["x"]),
                "--y",
                str(exp.goal["y"]),
                "--yaw",
                str(exp.goal["yaw"]),
                "--wait",
                "--timeout",
                str(timeout_s),
            ]
        ),
        env=env,
        log_path=session / "esc_goal.txt",
    )
    return int(proc.wait())
