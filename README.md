# social-nav-platform

## Origin

This repository is **original** to the handover family (experiment descriptors,
supervisor, Nav2/ESC profiles, campaign crowds, CLI). It is not a fork.

Vendored ROS messages (not authored here):

- `people_msgs` — [wg-perception/people](https://github.com/wg-perception/people) (BSD, Willow Garage)
- `pedsim_msgs` — [stephenadhi/pedsim_ros](https://github.com/stephenadhi/pedsim_ros) `humble` (BSD)

Sibling trees **are** derived: wrapper and HuNav from robotics-upo, ESC from
Cardiff, worlds/robots from CUCR / Hello Robot / Pollen. Those READMEs state
the upstream URL and why the tree exists.

Front door for the lab handover family: experiment descriptors, Nav2/ESC
profiles, campaign crowds, lab robot YAML, and a `social-nav` CLI.

This tree does **not** own CUCR USD binaries (see `social-nav-assets`) or the
generic Isaac/HuNav runtime (`hunav-isaac-wrapper-jazzy`). NVIDIA Isaac Sim is
runtime-only.

Fourteen named experiments (seven CUCR worlds × ESC then Nav2). Git example
results: museum Reachy and hospital Stretch `metrics_cited.csv` only.

## Install

Host pins, family tags, sibling trees, USD tarball, overlay build: [docs/installation.md](docs/installation.md).

```bash
sudo ./scripts/bootstrap.sh --install-system-deps
./scripts/unpack-assets.sh
source /opt/ros/jazzy/setup.bash
./scripts/build.sh
./scripts/doctor.sh
./scripts/test.sh
```

## Run

[docs/quickstart.md](docs/quickstart.md)

```bash
./scripts/social-nav list experiments
./scripts/social-nav explain museum-reachy-nav2
./scripts/social-nav run museum-reachy-nav2
./scripts/social-nav run museum-reachy-nav2 --execute
```

`run` without `--execute` validates and writes a session plan. `--execute`
starts Isaac keepalive in one process group, waits for `/scan` and `/odom`,
starts hunav_evaluator, then **either** Nav2 **or** ESC and sends the
descriptor goal. Cameras stay **on**. Optional `--monitor` opens RViz after
`/scan`. Do not pass `--disable-cameras`.

## Extend

[docs/extending.md](docs/extending.md) — worlds, robots, crowds, planners, metrics.

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
