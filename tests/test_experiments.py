"""Experiment lock and licence checks (no Isaac Sim)."""

from __future__ import annotations

from pathlib import Path

from social_nav_runner.experiments import load_all, platform_root, validate_tree


ROOT = platform_root()


def test_validate_tree() -> None:
    assert validate_tree(ROOT) == []


def test_fourteen_experiments_one_robot() -> None:
    exps = load_all(ROOT)
    assert len(exps) == 14
    stacks = {(e.world, e.robot, e.stack) for e in exps}
    assert len(stacks) == 14
    for exp in exps:
        assert exp.cameras and exp.lidar
        assert exp.robot in {"stretch", "reachy"}


def test_museum_reachy_pose() -> None:
    exp = next(e for e in load_all(ROOT) if e.id == "museum-reachy-nav2")
    assert exp.spawn["x"] == 2.0
    assert exp.spawn["y"] == -8.0
    assert exp.goal["x"] == 1.5
    assert exp.goal["y"] == 6.5


def test_no_lab_home_in_text() -> None:
    hits = []
    skip = {".png", ".bt", ".csv"}
    for path in ROOT.rglob("*"):
        if not path.is_file() or path.suffix in skip:
            continue
        if ".git" in path.parts or "tests" in path.parts:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        if "/home/osamuzahid" in text:
            hits.append(str(path.relative_to(ROOT)))
    assert hits == []


def test_bsd_licence_files() -> None:
    people = ROOT / "src" / "vendor" / "people_msgs" / "LICENSE"
    pedsim = ROOT / "src" / "vendor" / "pedsim_msgs" / "LICENSE"
    assert "BSD" in people.read_text(encoding="utf-8") or "Redistribution" in people.read_text(encoding="utf-8")
    assert "Redistribution" in pedsim.read_text(encoding="utf-8")


def test_example_results_present() -> None:
    for folder in (
        "museum_reachy_esc",
        "museum_reachy_nav2",
        "hospital_stretch_esc",
        "hospital_stretch_nav2",
    ):
        csv = ROOT / "results" / "examples" / folder / "metrics_cited.csv"
        assert csv.is_file()
        assert "path_length" in csv.read_text(encoding="utf-8").splitlines()[0]


def test_crowds_not_behaviors() -> None:
    crowds = list((ROOT / "config" / "crowds").glob("*_crowd.yaml"))
    assert len(crowds) == 7
    assert not list((ROOT / "config" / "crowds").glob("*_behaviors.yaml"))


def test_components_lock_has_full_shas() -> None:
    import yaml

    lock = yaml.safe_load((ROOT / "components.lock.yaml").read_text(encoding="utf-8"))
    for name in ("wrapper", "hunav", "esc", "assets"):
        sha = lock[name]["sha"]
        assert len(sha) == 40
        assert all(c in "0123456789abcdef" for c in sha)


def test_run_execute_fails_closed() -> None:
    from social_nav_runner.cli import main

    rc = main(["run", "museum-reachy-esc", "--execute"])
    assert rc == 3
