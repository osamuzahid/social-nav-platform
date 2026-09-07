"""social-nav CLI (list / explain / validate / run plan)."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from social_nav_runner.experiments import load_all, load_experiment, platform_root, validate_tree


def _cmd_list(args: argparse.Namespace) -> int:
    root = platform_root()
    kind = args.what
    if kind == "worlds":
        for path in sorted((root / "config" / "worlds").glob("*.yaml")):
            print(path.stem)
        return 0
    if kind == "robots":
        for path in sorted((root / "config" / "robots").iterdir()):
            if (path / "robot.yaml").is_file():
                print(path.name)
        return 0
    if kind == "experiments":
        for exp in load_all(root):
            print(f"{exp.id:32} {exp.world:16} {exp.robot:8} {exp.stack}")
        return 0
    print("unknown list target", file=sys.stderr)
    return 2


def _cmd_explain(args: argparse.Namespace) -> int:
    root = platform_root()
    path = root / "config" / "experiments" / f"{args.experiment_id}.yaml"
    if not path.is_file():
        print(f"unknown experiment {args.experiment_id}", file=sys.stderr)
        return 2
    exp = load_experiment(path, root)
    print(f"id:       {exp.id}")
    print(f"world:    {exp.world}")
    print(f"robot:    {exp.robot}")
    print(f"crowd:    {exp.crowd}")
    print(f"planner:  {exp.planner}")
    print(
        f"spawn:    ({exp.spawn['x']}, {exp.spawn['y']}) yaw {exp.spawn['yaw']}"
    )
    print(f"goal:     ({exp.goal['x']}, {exp.goal['y']}) yaw {exp.goal['yaw']}")
    print(f"sensors:  lidar={exp.lidar} cameras={exp.cameras}")
    print("note:     scored hops keep cameras on; one robot; ESC and Nav2 are separate arms")
    return 0


def _cmd_validate(_args: argparse.Namespace) -> int:
    errors = validate_tree()
    if errors:
        for err in errors:
            print(f"FAIL {err}", file=sys.stderr)
        return 1
    print("OK 14 experiments")
    return 0


def _cmd_run(args: argparse.Namespace) -> int:
    root = platform_root()
    path = root / "config" / "experiments" / f"{args.experiment_id}.yaml"
    if not path.is_file():
        print(f"unknown experiment {args.experiment_id}", file=sys.stderr)
        return 2
    errors = validate_tree(root)
    if errors:
        for err in errors:
            print(f"configuration_error {err}", file=sys.stderr)
        return 1
    exp = load_experiment(path, root)
    if not args.execute:
        session = {
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
            "execute": False,
        }
        out = Path(args.session_dir) if args.session_dir else None
        if out is None:
            stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
            out = root / "cache" / "sessions" / f"{stamp}_{exp.id}"
        out.mkdir(parents=True, exist_ok=True)
        (out / "plan.json").write_text(json.dumps(session, indent=2, sort_keys=True) + "\n")
        print(str(out / "plan.json"))
        return 0
    from social_nav_runner.supervisor import execute_experiment

    session_dir = Path(args.session_dir) if args.session_dir else None
    return execute_experiment(
        args.experiment_id,
        root=root,
        session_dir=session_dir,
        monitor=bool(getattr(args, "monitor", False)),
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="social-nav")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_list = sub.add_parser("list")
    p_list.add_argument("what", choices=("worlds", "robots", "experiments"))
    p_list.set_defaults(func=_cmd_list)

    p_ex = sub.add_parser("explain")
    p_ex.add_argument("experiment_id")
    p_ex.set_defaults(func=_cmd_explain)

    p_val = sub.add_parser("validate")
    p_val.set_defaults(func=_cmd_validate)

    p_run = sub.add_parser("run")
    p_run.add_argument("experiment_id")
    p_run.add_argument("--execute", action="store_true")
    p_run.add_argument("--session-dir")
    p_run.add_argument("--monitor", action="store_true", help="Open RViz after /scan")
    p_run.set_defaults(func=_cmd_run)

    args = parser.parse_args(argv)
    return int(args.func(args))
