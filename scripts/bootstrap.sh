#!/usr/bin/env bash
# Check-only by default. Does not sudo, delete workspaces, or create remotes.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
INSTALL_DEPS=0
for arg in "$@"; do
  case "$arg" in
    --install-system-deps) INSTALL_DEPS=1 ;;
    -h|--help)
      echo "Usage: $0 [--install-system-deps]"
      echo "Default: run doctor.sh (sibling SHAs, USD bundle, unpacked worlds)."
      echo "--install-system-deps: apt packages (needs root). Does not install Isaac Sim or lightsfm."
      exit 0
      ;;
    *)
      echo "unknown argument: $arg" >&2
      exit 2
      ;;
  esac
done

if [[ "$INSTALL_DEPS" -eq 1 ]]; then
  if [[ "${EUID}" -ne 0 ]]; then
    echo "dependency_error: --install-system-deps needs root for apt" >&2
    exit 1
  fi
  apt-get update
  apt-get install -y \
    python3-yaml python3-pytest python3-colcon-common-extensions \
    liboctomap-dev zstd \
    ros-jazzy-navigation2 ros-jazzy-nav2-bringup ros-jazzy-nav2-behavior-tree \
    ros-jazzy-behaviortree-cpp \
    ros-jazzy-grid-map ros-jazzy-pcl-ros ros-jazzy-cv-bridge ros-jazzy-ompl
  exit 0
fi

exec "$ROOT/scripts/doctor.sh"
