# Limitations (v0.1.0-candidate)

- `social-nav run --execute` starts one process group (Isaac keepalive, then
  Nav2 **or** ESC, plus hunav_evaluator). It does not restore a GNOME terminal
  farm.
- `--execute` fails closed when Isaac python, world/robot USDs, occupancy, the
  HuNav overlay (`SOCIAL_NAV_ROS_SETUP`), or (for ESC) the octomap /
  `SOCIAL_NAV_ESC_SETUP` is missing. Set `SOCIAL_NAV_ISAAC_PATH` if Isaac is not
  at `$HOME/isaacsim/python.sh`.
- `GOAL=SUCCEEDED` plus `metrics_cited.csv` (last HuNav row) copies into
  `results/runs/<id>/` and refuses overwrite.
- Bootstrap is check-only unless `--install-system-deps` (apt only).
- Sibling handover trees are expected next to this checkout. There is no
  GitHub clone step on this candidate.
- PhysX Stretch (`stretch_wheeled`) is rejected.
- Simultaneous multi-robot episodes are out of scope.
- Mixed HuNav behaviour trees are not scored (campaign crowds are type 2).
- CUCR historical world SHAs, `lightsfm` git SHA, and lab org URLs stay
  unknown.
