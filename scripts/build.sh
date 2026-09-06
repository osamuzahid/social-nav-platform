#!/usr/bin/env bash
# colcon-build vendored message packages when ROS 2 Jazzy is sourced.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
if [[ "${ROS_DISTRO:-}" != "jazzy" ]]; then
  echo "dependency_error: source ROS 2 Jazzy first" >&2
  exit 1
fi
cd "$ROOT"
colcon build --symlink-install --paths src/vendor/people_msgs src/vendor/pedsim_msgs
