# Quickstart

Install first: [installation.md](installation.md). From `social-nav-platform`:

```bash
source /opt/ros/jazzy/setup.bash
./scripts/social-nav list experiments
./scripts/social-nav explain museum-reachy-nav2
./scripts/social-nav run museum-reachy-nav2
./scripts/social-nav run museum-reachy-nav2 --execute
```

`run` without `--execute` writes `cache/sessions/<stamp>_<id>/plan.json`. `--execute` starts Isaac, waits for `/scan` and `/odom`, starts hunav_evaluator, then **either** Nav2 **or** ESC, and sends the descriptor goal.

Optional `--monitor` opens RViz after `/scan`. Do not pass `--disable-cameras`.

A second arm on the same world/robot:

```bash
./scripts/social-nav run museum-reachy-esc --execute
```

Do not start Nav2 and ESC together.

`GOAL=SUCCEEDED` plus `metrics_cited.csv` copies into `results/runs/<id>/` and refuses overwrite. Failed hops stay in `cache/sessions/`.

Isaac needs a working display (scored hops are windowed). If `python.sh` is not at `$HOME/isaacsim/python.sh`, set `SOCIAL_NAV_ISAAC_PATH`.

If `/clock` is already on the ROS domain, close leftover Isaac and retry. See [troubleshooting.md](troubleshooting.md).
