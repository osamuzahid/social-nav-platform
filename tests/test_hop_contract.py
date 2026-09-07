"""Freeze hop contract: relocatable Nav2 params, PlannerReady, ESC bounds."""

from __future__ import annotations

from pathlib import Path

from social_nav_runner.errors import HopError
from social_nav_runner.esc import planning_bounds_argv
from social_nav_runner.experiments import platform_root
from social_nav_runner.layout import Layout
from social_nav_runner.nav2 import (
    materialize_nav2_params,
    nav2_bringup_failure,
    nav2_goal_verdict,
)
from social_nav_runner.waiters import lifecycle_is_active

ROOT = platform_root()


def test_git_nav2_yaml_keeps_bt_basename() -> None:
    for name in ("nav2_reachy.yaml", "nav2_stretch.yaml"):
        text = (ROOT / "config" / "planners" / name).read_text(encoding="utf-8")
        assert 'default_nav_to_pose_bt_xml: "navigate_to_pose_w_replanning_20hz.xml"' in text
        assert "/home/" not in text


def test_materialize_nav2_params_absolute_bt_xml(tmp_path: Path) -> None:
    layout = Layout.discover(ROOT)
    dest = tmp_path / "nav2_params.yaml"
    out = materialize_nav2_params(layout, "reachy", dest)
    text = out.read_text(encoding="utf-8")
    bt = layout.nav2_bt_xml()
    assert bt.is_file()
    assert bt.is_absolute()
    assert f'default_nav_to_pose_bt_xml: "{bt}"' in text
    assert text.count("default_nav_to_pose_bt_xml:") == 1


def test_nav2_bringup_xml_miss_is_failure() -> None:
    log = (
        "bt_navigator: Couldn't open input XML file: "
        "navigate_to_pose_w_replanning_20hz.xml\n"
        "Failed to change state for node: bt_navigator\n"
        "Aborting bringup.\n"
    )
    assert nav2_bringup_failure(log) == "Couldn't open input XML file"


def test_nav2_rejected_goal_is_not_unknown() -> None:
    text = "Action server is inactive. Rejecting the goal.\nGoal was rejected.\n"
    assert nav2_goal_verdict(text, 0) == "GOAL=REJECTED"


def test_lifecycle_active_not_inactive() -> None:
    assert lifecycle_is_active("active [3]")
    assert not lifecycle_is_active("inactive [2]")
    assert not lifecycle_is_active("")


def test_esc_bounds_match_freeze_argv() -> None:
    argv = planning_bounds_argv(
        {"esc_bounds_x": [-35.0, 25.0], "esc_bounds_y": [-2.0, 25.0]}
    )
    assert argv == [
        "-p",
        "planning_bounds_x:=[-35.0,25.0]",
        "-p",
        "planning_bounds_y:=[-2.0,25.0]",
    ]
    assert planning_bounds_argv({}) == []


def test_materialize_missing_key_fails(tmp_path: Path) -> None:
    layout = Layout.discover(ROOT)
    src = tmp_path / "empty.yaml"
    src.write_text("bt_navigator:\n  ros__parameters: {}\n", encoding="utf-8")

    class _Fake:
        def nav2_params(self, robot: str):
            return src

        def nav2_bt_xml(self):
            return layout.nav2_bt_xml()

    try:
        materialize_nav2_params(_Fake(), "reachy", tmp_path / "out.yaml")  # type: ignore[arg-type]
    except HopError as exc:
        assert exc.category == "configuration_error"
    else:
        raise AssertionError("expected HopError")
