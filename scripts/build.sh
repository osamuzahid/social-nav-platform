#!/usr/bin/env bash
# Build sibling overlays: platform msgs, HuNav, wrapper, ESC.
# Source /opt/ros/jazzy first, or this script sources it with set +u.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
LOCK="$ROOT/components.lock.yaml"

if [[ ! -f /opt/ros/jazzy/setup.bash ]]; then
  echo "dependency_error: ROS 2 Jazzy setup.bash not found" >&2
  exit 1
fi

source_setup() {
  set +u
  # shellcheck disable=SC1090
  source "$1"
  set -u
}

# Do not inherit another workspace's overlay (this script stacks Jazzy + siblings).
unset COLCON_PREFIX_PATH AMENT_PREFIX_PATH CMAKE_PREFIX_PATH

read_path() {
  python3 - "$LOCK" "$ROOT" "$1" <<'PY'
import sys
from pathlib import Path
import yaml
lock = yaml.safe_load(Path(sys.argv[1]).read_text(encoding="utf-8"))
root = Path(sys.argv[2])
print((root / lock[sys.argv[3]]["path"]).resolve())
PY
}

HUNAV="$(read_path hunav)"
WRAPPER="$(read_path wrapper)"
ESC="$(read_path esc)"

if [[ ! -f /usr/local/include/lightsfm/sfm.hpp ]]; then
  echo "dependency_error: lightsfm headers missing at /usr/local/include/lightsfm" >&2
  echo "Install robotics-upo/lightsfm into /usr/local, then rebuild." >&2
  exit 1
fi

source_setup /opt/ros/jazzy/setup.bash

echo "building platform message packages"
cd "$ROOT"
colcon build --symlink-install --paths src/vendor/people_msgs src/vendor/pedsim_msgs
source_setup "$ROOT/install/setup.bash"

echo "building hunav-sim-jazzy"
cd "$HUNAV"
colcon build --symlink-install --base-paths . \
  --packages-select hunav_msgs hunav_agent_manager hunav_evaluator hunav_sim \
  --packages-ignore hunav_rviz2_panel
source_setup "$HUNAV/install/setup.bash"

echo "building hunav-isaac-wrapper-jazzy"
cd "$WRAPPER"
colcon build --symlink-install
source_setup "$WRAPPER/install/setup.bash"

echo "building esc-nav-jazzy"
cd "$ESC"
colcon build --symlink-install --base-paths .

echo "build OK"
echo "HuNav overlay: $HUNAV/install/setup.bash"
echo "ESC overlay:   $ESC/install/setup.bash"
