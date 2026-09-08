"""Resolve sibling handover trees and SOCIAL_NAV_* overlay env."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from social_nav_runner.experiments import Experiment, platform_root

CAMPAIGN_WORLDS = (
    "museum",
    "hospital",
    "office",
    "bookstore",
    "house_museum",
    "small_house",
    "small_warehouse",
)
CAMPAIGN_ROBOTS = ("stretch", "reachy")


def _load_lock(root: Path) -> dict[str, Any]:
    return yaml.safe_load((root / "components.lock.yaml").read_text(encoding="utf-8"))


def isaac_python() -> Path:
    raw = os.environ.get("SOCIAL_NAV_ISAAC_PATH", "").strip()
    if raw:
        return Path(raw).expanduser()
    return Path.home() / "isaacsim" / "python.sh"


def ros_setups(root: Path | None = None) -> list[Path]:
    """Extra workspaces to source after /opt/ros/jazzy."""
    out: list[Path] = []
    seen: set[Path] = set()

    def _add(path: Path) -> None:
        path = path.expanduser()
        if path.is_file() and path not in seen:
            seen.add(path)
            out.append(path)

    for key in ("SOCIAL_NAV_ROS_SETUP", "SOCIAL_NAV_ESC_SETUP"):
        raw = os.environ.get(key, "").strip()
        if not raw:
            continue
        for part in raw.split(":"):
            _add(Path(part))
    base = (root or platform_root()).resolve()
    for rel in (
        Path("install") / "setup.bash",
        Path("..") / "hunav-sim-jazzy" / "install" / "setup.bash",
        Path("..") / "hunav-isaac-wrapper-jazzy" / "install" / "setup.bash",
        Path("..") / "esc-nav-jazzy" / "install" / "setup.bash",
    ):
        _add(base / rel)
    return out


@dataclass(frozen=True)
class Layout:
    platform: Path
    wrapper: Path
    hunav: Path
    esc: Path
    assets: Path

    @classmethod
    def discover(cls, root: Path | None = None) -> Layout:
        root = (root or platform_root()).resolve()
        lock = _load_lock(root)
        return cls(
            platform=root,
            wrapper=(root / lock["wrapper"]["path"]).resolve(),
            hunav=(root / lock["hunav"]["path"]).resolve(),
            esc=(root / lock["esc"]["path"]).resolve(),
            assets=(root / lock["assets"]["path"]).resolve(),
        )

    @property
    def worlds(self) -> Path:
        return self.assets / "worlds"

    @property
    def maps(self) -> Path:
        return self.assets / "maps"

    @property
    def robot_usd(self) -> Path:
        return self.assets / "robots"

    @property
    def robots_yaml(self) -> Path:
        return self.platform / "config" / "robots"

    @property
    def crowds(self) -> Path:
        return self.platform / "config" / "crowds"

    @property
    def keepalive(self) -> Path:
        return self.platform / "tools" / "nav2_isaac_keepalive.py"

    def overlay_env(self) -> dict[str, str]:
        env = os.environ.copy()
        env.update(
            {
                "SOCIAL_NAV_ROBOTS": str(self.robots_yaml),
                "SOCIAL_NAV_ROBOT_USD": str(self.robot_usd),
                "SOCIAL_NAV_WORLDS": str(self.worlds),
                "SOCIAL_NAV_MAPS": str(self.maps),
                "SOCIAL_NAV_SCENARIOS": str(self.crowds),
                "SOCIAL_NAV_WRAPPER": str(self.wrapper),
                "SOCIAL_NAV_PLATFORM": str(self.platform),
                "OMNI_KIT_ACCEPT_EULA": env.get("OMNI_KIT_ACCEPT_EULA", "YES"),
                "ROS_DOMAIN_ID": env.get("ROS_DOMAIN_ID", "0"),
                "HUNAV_ISAAC_PROFILE": env.get("HUNAV_ISAAC_PROFILE", "debug"),
                "HUNAV_ISAAC_HEADLESS": env.get("HUNAV_ISAAC_HEADLESS", "0"),
                "HUNAV_LAB_SENSORS": "1",
                "HUNAV_LAB_LIDAR": "1",
                "HUNAV_LAB_CAMERAS": "1",
                "HUNAV_BEHAVIOR_LABELS": env.get("HUNAV_BEHAVIOR_LABELS", "1"),
                "HUNAV_START_EVALUATOR": "0",
                "PYTHONUNBUFFERED": "1",
            }
        )
        fastrtps = self.platform / "config" / "planners" / "fastrtps_no_shm.xml"
        if fastrtps.is_file():
            env.setdefault("FASTRTPS_DEFAULT_PROFILES_FILE", str(fastrtps))
            env.setdefault("RMW_FASTRTPS_USE_QOS_FROM_XML", "1")
        wrapper_src = self.wrapper / "src"
        extra = str(wrapper_src)
        existing = env.get("PYTHONPATH", "")
        env["PYTHONPATH"] = extra if not existing else extra + os.pathsep + existing
        return env

    def ros_child_env(self) -> dict[str, str]:
        """Nav2 / ESC / evaluator: system Python, no Isaac Kit on PYTHONPATH."""
        env = self.overlay_env()
        env["AMENT_PYTHON_EXECUTABLE"] = "/usr/bin/python3"
        parts = [
            p
            for p in env.get("PYTHONPATH", "").split(os.pathsep)
            if p and "isaacsim" not in p.lower() and "isaac-sim" not in p.lower()
        ]
        env["PYTHONPATH"] = os.pathsep.join(parts)
        return env

    def missing_runtime_assets(self) -> list[str]:
        missing: list[str] = []
        for world in CAMPAIGN_WORLDS:
            usd = self.worlds / f"{world}.usd"
            if not usd.is_file():
                missing.append(str(usd))
        for robot in CAMPAIGN_ROBOTS:
            usd = self.robot_usd / robot / f"{robot}.usd"
            if not usd.is_file():
                missing.append(str(usd))
        return missing

    def hunav_overlay_ok(self) -> bool:
        raw = os.environ.get("SOCIAL_NAV_ROS_SETUP", "").strip()
        if raw and any(Path(p).expanduser().is_file() for p in raw.split(":")):
            return True
        return (self.hunav / "install" / "setup.bash").is_file()

    def esc_overlay_ok(self) -> bool:
        raw = os.environ.get("SOCIAL_NAV_ESC_SETUP", "").strip()
        if raw and any(Path(p).expanduser().is_file() for p in raw.split(":")):
            return True
        return (self.esc / "install" / "setup.bash").is_file()

    def world_spec(self, world: str) -> dict[str, Any]:
        path = self.platform / "config" / "worlds" / f"{world}.yaml"
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError(f"{path} is not a mapping")
        return data

    def occupancy_yaml(self, world: str) -> Path:
        rel = str(self.world_spec(world).get("occupancy") or f"maps/{world}.yaml")
        return self.assets / rel

    def octomap_bt(self, world: str) -> Path:
        rel = str(self.world_spec(world).get("octomap") or f"maps/{world}.bt")
        return self.assets / rel

    def nav2_params(self, robot: str) -> Path:
        return self.platform / "config" / "planners" / f"nav2_{robot}.yaml"

    def nav2_bt_xml(self) -> Path:
        return self.platform / "config" / "planners" / "navigate_to_pose_w_replanning_20hz.xml"

    def esc_params(self, robot: str) -> Path:
        return self.platform / "config" / "planners" / f"esc_{robot}.yaml"

    def laser_frame(self, robot: str) -> str:
        return "lidar_link" if robot == "reachy" else "laser"

    def preflight(self, exp: Experiment) -> list[str]:
        errors: list[str] = []
        isaac = isaac_python()
        if not isaac.is_file() or not os.access(isaac, os.X_OK):
            errors.append(
                f"dependency_error: Isaac python not found at {isaac} "
                "(set SOCIAL_NAV_ISAAC_PATH)"
            )
        if not self.keepalive.is_file():
            errors.append(f"configuration_error: missing keepalive {self.keepalive}")
        usd = self.worlds / f"{exp.world}.usd"
        if not usd.is_file():
            errors.append(f"asset_error: missing world USD {usd}")
        robot_usd = self.robot_usd / exp.robot / f"{exp.robot}.usd"
        if not robot_usd.is_file():
            errors.append(f"asset_error: missing robot USD {robot_usd}")
        occ = self.occupancy_yaml(exp.world)
        if not occ.is_file():
            errors.append(f"asset_error: missing occupancy {occ}")
        if exp.stack == "esc":
            bt = self.octomap_bt(exp.world)
            if not bt.is_file():
                errors.append(f"asset_error: missing octomap {bt}")
            if not self.esc_params(exp.robot).is_file():
                errors.append(f"configuration_error: missing {self.esc_params(exp.robot)}")
        else:
            if not self.nav2_params(exp.robot).is_file():
                errors.append(f"configuration_error: missing {self.nav2_params(exp.robot)}")
            if not self.nav2_bt_xml().is_file():
                errors.append(f"configuration_error: missing {self.nav2_bt_xml()}")
        jazzy = Path("/opt/ros/jazzy/setup.bash")
        if not jazzy.is_file():
            errors.append("dependency_error: ROS 2 Jazzy setup.bash not found")
        crowd = self.crowds / f"{exp.crowd}.yaml"
        if not crowd.is_file():
            errors.append(f"configuration_error: missing crowd {crowd}")
        if not self.hunav_overlay_ok():
            errors.append(
                "dependency_error: run ./scripts/build.sh (or set SOCIAL_NAV_ROS_SETUP) "
                "so hunav_agent_manager is on the overlay"
            )
        if exp.stack == "esc" and not self.esc_overlay_ok():
            errors.append(
                "dependency_error: run ./scripts/build.sh (or set SOCIAL_NAV_ESC_SETUP) "
                "so ESC nodes are on the overlay"
            )
        metrics_yaml = self.platform / "config" / "metrics" / "campaign-v1.yaml"
        if not metrics_yaml.is_file():
            errors.append(f"configuration_error: missing {metrics_yaml}")
        return errors
