# Limitations (v0.2.1)

- `social-nav run --execute` starts one process group (Isaac keepalive, then
  Nav2 **or** ESC, plus hunav_evaluator). It does not restore a GNOME terminal
  farm.
- `--execute` fails closed when Isaac python, world/robot USDs, occupancy,
  the sibling HuNav overlay (`../hunav-sim-jazzy/install/setup.bash` after
  `./scripts/build.sh`, or `SOCIAL_NAV_ROS_SETUP`), or (for ESC) the octomap /
  ESC overlay is missing. Set `SOCIAL_NAV_ISAAC_PATH` if Isaac is not at
  `$HOME/isaacsim/python.sh`.
- `GOAL=SUCCEEDED` plus `metrics_cited.csv` (last HuNav row) copies into
  `results/runs/<id>/` and refuses overwrite.
- Bootstrap is check-only unless `--install-system-deps`. That path installs
  and holds the lock apt versions (the ROS and Ubuntu packages this family
  was built and tested against). It does not install Isaac Sim or lightsfm.
- Doctor fails when a lock apt package is installed at the wrong version.
  Isaac, driver, lightsfm, pandas/numpy, and Assimp mismatches are notes.
- Sibling handover trees are expected next to this checkout. `./scripts/build.sh`
  colcon-builds them in place. Bootstrap does not clone them.
- PhysX Stretch (`stretch_wheeled`) is rejected.
- Simultaneous multi-robot episodes are out of scope.
- Mixed HuNav behaviour trees are not scored (campaign crowds are type 2).
- CUCR historical world SHAs and the `lightsfm` git SHA stay unknown.
