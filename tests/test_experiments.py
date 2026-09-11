"""Experiment lock and licence checks (no Isaac Sim)."""

from __future__ import annotations

import subprocess

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
    tracked = subprocess.check_output(
        ["git", "ls-files"], cwd=ROOT, text=True
    ).splitlines()
    for rel in tracked:
        if rel.startswith("tests/") or "/tests/" in rel:
            continue
        path = ROOT / rel
        if not path.is_file() or path.suffix in skip:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        if "/home/" in text:
            hits.append(rel)
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


def test_components_lock_apt_versions() -> None:
    import yaml

    lock = yaml.safe_load((ROOT / "components.lock.yaml").read_text(encoding="utf-8"))
    apt = lock["apt"]
    assert apt["ros_snapshot"].startswith("http://snapshots.ros.org/")
    pkgs = apt["packages"]
    assert pkgs["ros-jazzy-navigation2"].startswith("1.3.12-")
    assert pkgs["ros-jazzy-nav2-smac-planner"].startswith("1.3.12-")
    assert pkgs["ros-jazzy-nav2-mppi-controller"].startswith("1.3.12-")
    assert pkgs["ros-jazzy-behaviortree-cpp"].startswith("4.9.0-")
    assert pkgs["ros-jazzy-cv-bridge"].startswith("4.1.0-1noble.20260615")
    assert pkgs["ros-jazzy-grid-map"].startswith("2.2.2-2noble.20260615")
    assert pkgs["ros-jazzy-pcl-ros"].startswith("2.6.4-")
    assert pkgs["ros-jazzy-ompl"].startswith("1.7.0-")
    assert "python3-yaml" in pkgs
    assert "liboctomap-dev" in pkgs


def test_components_lock_records_host_environment() -> None:
    import yaml

    lock = yaml.safe_load((ROOT / "components.lock.yaml").read_text(encoding="utf-8"))
    env = lock["environment"]
    assert env["isaac_version"].startswith("6.0.1")
    assert env["python"].startswith("3.12")
    assert env["pandas"]
    assert env["numpy"]
    assert env["assimp_utils"]
    assert env["nvidia_driver_minimum"].startswith("595.")
    assert len(env["lightsfm_include_sha256"]) == 64


def test_run_execute_fails_closed_without_isaac(tmp_path, monkeypatch) -> None:
    from social_nav_runner import supervisor

    monkeypatch.setattr(
        supervisor, "_archive_dir", lambda root, exp: tmp_path / exp.id
    )
    rc = supervisor.execute_experiment("museum-reachy-esc")
    assert rc == 3


def test_unknown_experiment() -> None:
    from social_nav_runner.cli import main

    assert main(["run", "not-a-real-hop", "--execute"]) == 2


def test_refuse_archive_overwrite() -> None:
    from social_nav_runner.cli import main

    dest = ROOT / "results" / "runs" / "museum-reachy-nav2"
    dest.mkdir(parents=True, exist_ok=True)
    marker = dest / "stale.txt"
    marker.write_text("keep", encoding="utf-8")
    try:
        assert main(["run", "museum-reachy-nav2", "--execute"]) == 4
    finally:
        marker.unlink(missing_ok=True)
        try:
            dest.rmdir()
        except OSError:
            pass


def test_cite_metrics_last_row(tmp_path) -> None:
    from social_nav_runner.evaluator import cite_metrics

    csv = tmp_path / "metrics.csv"
    csv.write_text("h1,h2\na,1\nb,2\n", encoding="utf-8")
    cited = cite_metrics(tmp_path)
    assert cited is not None
    assert cited.read_text(encoding="utf-8") == "h1,h2\nb,2\n"


def test_overlay_env_points_at_siblings() -> None:
    from social_nav_runner.layout import CAMPAIGN_WORLDS, Layout

    layout = Layout.discover(ROOT)
    env = layout.overlay_env()
    assert env["SOCIAL_NAV_SCENARIOS"].endswith("config/crowds")
    assert env["SOCIAL_NAV_ROBOTS"].endswith("config/robots")
    assert "hunav-isaac-wrapper-jazzy" in env["SOCIAL_NAV_WRAPPER"]
    worlds = {e.world for e in load_all(ROOT)}
    assert worlds <= set(CAMPAIGN_WORLDS)


def test_process_group_terminates_children() -> None:
    import os
    import time

    from social_nav_runner.processes import ProcessGroup

    pg = ProcessGroup()
    log = ROOT / "cache" / "sessions"
    log.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    pg.start(["sleep", "30"], env=env, log_path=log / "test_pg_a.log")
    pg.start(["sleep", "30"], env=env, log_path=log / "test_pg_b.log")
    assert pg.pgid is not None
    assert os.getpgid(pg._children[0].pid) == pg.pgid
    assert os.getpgid(pg._children[1].pid) == pg.pgid
    pg.terminate(grace_s=5.0)
    time.sleep(0.2)
    assert all(p.poll() is not None for p in pg._children)
