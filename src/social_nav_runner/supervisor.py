"""One-supervisor execute: Isaac keepalive, then Nav2 xor ESC, then archive."""

from __future__ import annotations

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

from social_nav_runner.errors import HopError, as_hop
from social_nav_runner.esc import bringup_esc, esc_goal_verdict, send_esc_goal
from social_nav_runner.evaluator import (
    cite_metrics,
    start_evaluator,
    start_recording,
    stop_recording,
    wait_evaluator_ready,
)
from social_nav_runner.experiments import Experiment, load_experiment, platform_root, validate_tree
from social_nav_runner.layout import Layout, isaac_python
from social_nav_runner.nav2 import bringup_nav2, nav2_goal_verdict, send_nav2_goal
from social_nav_runner.processes import ProcessGroup
from social_nav_runner.rosenv import sourced_argv
from social_nav_runner.waiters import topic_has_data, wait_log_marker, wait_topic


READY_TIMEOUT_S = 360.0
SENSOR_TIMEOUT_S = 120.0
GOAL_TIMEOUT_S = 600.0


def _session_dir(root: Path, exp: Experiment, requested: Path | None) -> Path:
    if requested is not None:
        requested.mkdir(parents=True, exist_ok=True)
        return requested
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out = root / "cache" / "sessions" / f"{stamp}_{exp.id}"
    out.mkdir(parents=True, exist_ok=True)
    return out


def _archive_dir(root: Path, exp: Experiment) -> Path:
    return root / "results" / "runs" / exp.id


def _write_plan(session: Path, exp: Experiment, execute: bool) -> None:
    payload = {
        "experiment": exp.id,
        "world": exp.world,
        "robot": exp.robot,
        "stack": exp.stack,
        "planner": exp.planner,
        "spawn": exp.spawn,
        "goal": exp.goal,
        "crowd": exp.crowd,
        "cameras": exp.cameras,
        "created": datetime.now(timezone.utc).isoformat(),
        "execute": execute,
    }
    (session / "plan.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def _verdict_from_logs(session: Path, stack: str, goal_rc: int) -> str:
    if stack == "nav2":
        text = (
            (session / "nav_goal.txt").read_text(errors="replace")
            if (session / "nav_goal.txt").is_file()
            else ""
        )
        return nav2_goal_verdict(text, goal_rc)
    text = (
        (session / "esc_goal.txt").read_text(errors="replace")
        if (session / "esc_goal.txt").is_file()
        else ""
    )
    return esc_goal_verdict(text, goal_rc)


def execute_experiment(
    experiment_id: str,
    *,
    root: Path | None = None,
    session_dir: Path | None = None,
    monitor: bool = False,
) -> int:
    root = root or platform_root()
    path = root / "config" / "experiments" / f"{experiment_id}.yaml"
    if not path.is_file():
        print(f"configuration_error: unknown experiment {experiment_id}", flush=True)
        return 2
    errors = validate_tree(root)
    if errors:
        for err in errors:
            print(f"configuration_error: {err}", flush=True)
        return 1
    exp = load_experiment(path, root)
    archive = _archive_dir(root, exp)
    if archive.is_dir() and any(archive.iterdir()):
        print(f"archive_error: refuse overwrite {archive}", flush=True)
        return 4
    layout = Layout.discover(root)
    pre = layout.preflight(exp)
    if pre:
        for err in pre:
            print(err, flush=True)
        return 3

    session = _session_dir(root, exp, session_dir)
    _write_plan(session, exp, execute=True)
    env = layout.overlay_env()
    ros_env = layout.ros_child_env()
    if topic_has_data(ros_env, "/clock", qos="best_effort") or topic_has_data(
        ros_env, "/clock", qos="reliable"
    ):
        print(
            "ros_readiness_error: ROS domain already has /clock "
            "(close leftover Isaac, then retry)",
            flush=True,
        )
        return 3

    pg = ProcessGroup()
    summary = session / "supervisor.log"
    goal_rc = 1
    recording = False
    try:
        isaac = isaac_python()
        isaac_cmd = sourced_argv(
            [
                str(isaac),
                str(layout.keepalive),
                "--seconds",
                "0",
                "--robot",
                exp.robot,
                "--world",
                exp.world,
                "--config",
                exp.crowd,
            ]
        )
        pg.start(isaac_cmd, env=env, log_path=session / "isaac.log", cwd=layout.wrapper)
        as_hop(
            "simulator_startup_error",
            wait_log_marker,
            session / "isaac.log",
            "[nav2_keepalive] ready",
            READY_TIMEOUT_S,
        )
        as_hop("ros_readiness_error", wait_topic, ros_env, "/scan", SENSOR_TIMEOUT_S, qos="best_effort")
        as_hop("ros_readiness_error", wait_topic, ros_env, "/odom", SENSOR_TIMEOUT_S, qos="best_effort")
        if monitor:
            rviz = root / "config" / "rviz" / f"{exp.robot}_scan.rviz"
            if rviz.is_file():
                pg.start(
                    sourced_argv(["rviz2", "-d", str(rviz)]),
                    env=ros_env,
                    log_path=session / "rviz.log",
                )
        start_evaluator(pg, layout, session, ros_env)
        as_hop("evaluation_error", wait_evaluator_ready, ros_env, READY_TIMEOUT_S)
        start_recording(ros_env, exp)
        recording = True
        if exp.stack == "esc":
            bringup_esc(pg, layout, exp, session, ros_env, READY_TIMEOUT_S)
            goal_rc = send_esc_goal(pg, layout, exp, session, ros_env, GOAL_TIMEOUT_S)
        else:
            bringup_nav2(pg, layout, exp, session, ros_env, READY_TIMEOUT_S)
            goal_rc = send_nav2_goal(pg, exp, session, ros_env, GOAL_TIMEOUT_S)
        verdict = _verdict_from_logs(session, exp.stack, goal_rc)
        summary.write_text(verdict + "\n", encoding="utf-8")
        print(verdict, flush=True)
    except HopError as exc:
        summary.write_text(f"{exc.category}: {exc}\n", encoding="utf-8")
        print(f"{exc.category}: {exc}", flush=True)
        print(str(session), flush=True)
        return 3
    except TimeoutError as exc:
        summary.write_text(f"ros_readiness_error: {exc}\n", encoding="utf-8")
        print(f"ros_readiness_error: {exc}", flush=True)
        print(str(session), flush=True)
        return 3
    except Exception as exc:
        summary.write_text(f"internal_error: {type(exc).__name__}: {exc}\n", encoding="utf-8")
        print(f"internal_error: {type(exc).__name__}: {exc}", flush=True)
        print(str(session), flush=True)
        return 3
    finally:
        if recording:
            try:
                stop_recording(ros_env)
            except Exception:
                pass
            cite_metrics(session)
        pg.terminate()

    verdict = summary.read_text(encoding="utf-8") if summary.is_file() else ""
    cited = session / "metrics_cited.csv"
    print(str(session), flush=True)
    if "GOAL=SUCCEEDED" not in verdict:
        return 5
    if not cited.is_file():
        print("evaluation_error: no metrics_cited.csv", flush=True)
        return 5
    if archive.exists() and any(archive.iterdir()):
        print(f"archive_error: refuse overwrite {archive}", flush=True)
        return 4
    archive.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(session, archive)
    print(str(archive), flush=True)
    return 0
