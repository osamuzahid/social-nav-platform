"""Load and validate campaign experiment descriptors."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

PLANNERS = {"nav2/smac-2d", "esc/extended-social-comfort"}
ROOT = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class Experiment:
    id: str
    world: str
    robot: str
    planner: str
    crowd: str
    route: str
    spawn: dict[str, float]
    goal: dict[str, float]
    cameras: bool
    lidar: bool
    path: Path

    @property
    def stack(self) -> str:
        return "esc" if self.planner.startswith("esc/") else "nav2"


def _load_yaml(path: Path) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path} is not a mapping")
    return data


def platform_root() -> Path:
    return ROOT


def list_experiment_files(root: Path | None = None) -> list[Path]:
    base = root or ROOT
    return sorted((base / "config" / "experiments").glob("*.yaml"))


def load_experiment(path: Path, root: Path | None = None) -> Experiment:
    root = root or ROOT
    data = _load_yaml(path)
    if data.get("schema_version") != 1:
        raise ValueError(f"{path.name}: schema_version must be 1")
    robots = data.get("robots") or []
    if len(robots) != 1:
        raise ValueError(f"{path.name}: v1 requires exactly one robot")
    robot = robots[0]["model"]
    planner = data["planner"]
    if planner not in PLANNERS:
        raise ValueError(f"{path.name}: unknown planner {planner}")
    sensors = data.get("sensors") or {}
    world = data["world"]
    route_id = data["route"]
    route = _load_yaml(root / "config" / "routes" / f"{route_id}.yaml")
    if route.get("world") != world:
        raise ValueError(f"{path.name}: route world mismatch")
    crowd = data["crowd"]
    crowd_path = root / "config" / "crowds" / f"{crowd}.yaml"
    if not crowd_path.is_file():
        raise ValueError(f"{path.name}: missing crowd {crowd_path}")
    return Experiment(
        id=str(data["id"]),
        world=world,
        robot=robot,
        planner=planner,
        crowd=crowd,
        route=route_id,
        spawn=route["spawn"],
        goal=route["goal"],
        cameras=bool(sensors.get("cameras", True)),
        lidar=bool(sensors.get("lidar", True)),
        path=path,
    )


def load_all(root: Path | None = None) -> list[Experiment]:
    root = root or ROOT
    return [load_experiment(p, root) for p in list_experiment_files(root)]


def validate_tree(root: Path | None = None) -> list[str]:
    """Return error strings (empty means OK)."""
    root = root or ROOT
    errors: list[str] = []
    experiments = []
    try:
        experiments = load_all(root)
    except (ValueError, OSError, yaml.YAMLError) as exc:
        return [str(exc)]
    ids = [e.id for e in experiments]
    if len(ids) != len(set(ids)):
        errors.append("duplicate experiment ids")
    if len(experiments) != 14:
        errors.append(f"expected 14 experiments, got {len(experiments)}")
    for exp in experiments:
        if not exp.cameras or not exp.lidar:
            errors.append(f"{exp.id}: scored hops keep cameras and lidar on")
        robot_yaml = root / "config" / "robots" / exp.robot / "robot.yaml"
        if not robot_yaml.is_file():
            errors.append(f"{exp.id}: missing {robot_yaml.relative_to(root)}")
        world_yaml = root / "config" / "worlds" / f"{exp.world}.yaml"
        if not world_yaml.is_file():
            errors.append(f"{exp.id}: missing world {exp.world}")
        if "stretch_wheeled" in exp.robot:
            errors.append(f"{exp.id}: PhysX Stretch is not supported")
    return errors
