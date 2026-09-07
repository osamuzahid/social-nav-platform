"""HuNav evaluator under system ROS Python (not Isaac python.sh)."""

from __future__ import annotations

import subprocess
import time
from pathlib import Path

from social_nav_runner.experiments import Experiment
from social_nav_runner.layout import Layout
from social_nav_runner.processes import ProcessGroup
from social_nav_runner.rosenv import sourced_argv
from social_nav_runner.waiters import wait_service, wait_topic


def start_evaluator(
    pg: ProcessGroup,
    layout: Layout,
    session: Path,
    env: dict[str, str],
) -> Path:
    metrics_yaml = layout.platform / "config" / "metrics" / "campaign-v1.yaml"
    result = session / "metrics"
    pg.start(
        sourced_argv(
            [
                "ros2",
                "run",
                "hunav_evaluator",
                "hunav_evaluator_node",
                "--ros-args",
                "--params-file",
                str(metrics_yaml),
                "-p",
                f"result_file:={result}",
            ]
        ),
        env=env,
        log_path=session / "evaluator_node.log",
    )
    return Path(str(result) + ".csv")


def wait_evaluator_ready(env: dict[str, str], timeout_s: float = 60.0) -> None:
    wait_topic(env, "/human_states", timeout_s, qos=None)
    wait_topic(env, "/robot_states", min(timeout_s, 60.0), qos=None)
    wait_service(env, "hunav_start_recording", timeout_s)


def start_recording(env: dict[str, str], exp: Experiment) -> None:
    payload = (
        "{experiment_tag: '%s', run_id: 1, robot_goal: {header: {frame_id: 'map'}, "
        "pose: {position: {x: %s, y: %s, z: 0.0}, orientation: {w: 1.0}}}}"
        % (exp.id, exp.goal["x"], exp.goal["y"])
    )
    subprocess.run(
        sourced_argv(
            [
                "ros2",
                "service",
                "call",
                "/hunav_start_recording",
                "hunav_msgs/srv/StartEvaluation",
                payload,
            ]
        ),
        env=env,
        check=False,
        timeout=30,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def stop_recording(env: dict[str, str]) -> None:
    subprocess.run(
        sourced_argv(
            [
                "ros2",
                "service",
                "call",
                "/hunav_stop_recording",
                "std_srvs/srv/Empty",
                "{}",
            ]
        ),
        env=env,
        check=False,
        timeout=30,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    time.sleep(3.0)


def cite_metrics(session: Path) -> Path | None:
    """Last data row only — HuNav appends leftover hops into metrics.csv."""
    csv = session / "metrics.csv"
    if not csv.is_file():
        return None
    lines = [ln for ln in csv.read_text(encoding="utf-8").splitlines() if ln.strip()]
    if len(lines) < 2:
        return None
    cited = session / "metrics_cited.csv"
    cited.write_text(lines[0] + "\n" + lines[-1] + "\n", encoding="utf-8")
    return cited
