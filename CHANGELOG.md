# Changelog

## Unreleased

## 0.2.4 — 2026-09-11

`--install-system-deps` verifies `snapshots.ros.org` with the vendored ROS
Snapshot builder key (`config/apt/ros-snapshot.asc`), not the live
`packages.ros.org` keyring. A failed `apt-get update` removes the leftover
snapshot source list.

## 0.2.3 — 2026-09-11

`--install-system-deps` installs and holds the lock apt versions so a host
matches the ROS and Ubuntu packages this family was built and tested against.
Doctor fails on apt version mismatch; Isaac, driver, lightsfm, pandas/numpy,
and Assimp are notes against the lock `environment` block. Home-path tests
scan `git ls-files`.

## 0.2.2 — 2026-09-08

Origin section on each family README: wrapper/HuNav/ESC are forks
(robotics-upo / Cardiff); assets lists CUCR / Hello Robot / Pollen;
platform is original plus vendored `people_msgs` / `pedsim_msgs`.

## 0.2.1 — 2026-09-08

Install path for sibling overlays: `unpack-assets.sh`, `build.sh` (HuNav,
wrapper, ESC), doctor checks campaign USDs. Docs: installation, quickstart,
extending, troubleshooting. Private remotes under `osamuzahid` (`v0.2.1`).

## 0.2.0 — 2026-09-08

`social-nav run --execute` runs the campaign hop (Isaac keepalive, evaluator,
then Nav2 or ESC). Sibling trees are pinned in `components.lock.yaml`. The
supervisor exits if `bt_navigator` disappears instead of hanging.

## 0.1.0-candidate — 2026-09-07

`social-nav run --execute` is a single process-group supervisor (Isaac
keepalive, hunav_evaluator, then Nav2 or ESC). Overlay env loads platform
robots/crowds and assets worlds/maps.

## 0.1.0-candidate — 2026-09-06

Local handover candidate. Fourteen campaign experiment descriptors, vendored
BSD message packages, doctor/bootstrap check-only, `social-nav` validate/list.
Native Isaac execute is not wired. No public GitHub remote.
