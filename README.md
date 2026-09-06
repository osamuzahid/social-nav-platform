# social-nav-platform

Front door for the lab handover family: experiment descriptors, Nav2/ESC
profiles, campaign crowds, lab robot YAML, and a `social-nav` CLI.

This tree does **not** own CUCR USD binaries (see `social-nav-assets`) or the
generic Isaac/HuNav runtime (`hunav-isaac-wrapper-jazzy`). NVIDIA Isaac Sim is
runtime-only.

Fourteen named experiments (seven CUCR worlds × ESC then Nav2). Git example
results: museum Reachy and hospital Stretch `metrics_cited.csv` only.

## Commands (no GPU)

```bash
./scripts/doctor.sh
./scripts/test.sh
./scripts/social-nav list experiments
./scripts/social-nav explain museum-reachy-nav2
./scripts/social-nav validate
./scripts/social-nav run museum-reachy-nav2
```

`run` validates and writes a session plan. Native Isaac execute is a later
overlay (one supervisor; not a set of GNOME terminals). Cameras stay **on**
for scored hops.

## Bootstrap

```bash
./scripts/bootstrap.sh
./scripts/bootstrap.sh --install-system-deps   # apt only with this flag
./scripts/build.sh                             # colcon vendor msgs if ROS 2 Jazzy is sourced
```

Default bootstrap is **check-only**. It verifies sibling handover trees at the
SHAs in [components.lock.yaml](components.lock.yaml). No GitHub remotes on this
candidate.

## Layout

```text
config/experiments/   14 campaign descriptors
config/crowds/        <world>_crowd.yaml (A1/A2 moving, A3–A5 standing)
config/robots/        stretch and reachy robot.yaml
config/planners/      Smac 2D Nav2 + ESC ExtendedSocialComfort
src/vendor/           people_msgs and pedsim_msgs (BSD licence files)
results/examples/     museum Reachy + hospital Stretch citeable CSVs
```

## Licence

- Platform tools and descriptors: **MIT** ([LICENSE](LICENSE)).
- `people_msgs`: **BSD** (Willow Garage) — `src/vendor/people_msgs/LICENSE`.
- `pedsim_msgs`: **BSD** (pedsim_ros authors) — `src/vendor/pedsim_msgs/LICENSE`.
- Stretch / Reachy / CUCR worlds: sibling `social-nav-assets`.
