#!/usr/bin/env bash
# Check-only by default. Does not sudo, delete workspaces, or create remotes.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
LOCK="$ROOT/components.lock.yaml"
INSTALL_DEPS=0
for arg in "$@"; do
  case "$arg" in
    --install-system-deps) INSTALL_DEPS=1 ;;
    -h|--help)
      echo "Usage: $0 [--install-system-deps]"
      echo "Default: run doctor.sh (sibling SHAs, USD bundle, unpacked worlds)."
      echo "--install-system-deps: apt packages at lock versions (needs root)."
      echo "Does not install Isaac Sim or lightsfm."
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
  KEYRING=/usr/share/keyrings/ros-archive-keyring.gpg
  if [[ ! -f "$KEYRING" ]]; then
    echo "dependency_error: ROS apt keyring missing at $KEYRING" >&2
    exit 1
  fi
  eval "$(python3 - "$LOCK" <<'PY'
import shlex, sys
from pathlib import Path
import yaml

lock = yaml.safe_load(Path(sys.argv[1]).read_text(encoding="utf-8"))
apt = lock["apt"]
print("SNAPSHOT=" + shlex.quote(apt["ros_snapshot"]))
print("SNAPSHOT_DIST=" + shlex.quote(apt["ros_snapshot_dist"]))
pkgs = []
for name, ver in apt["packages"].items():
    pkgs.append(f"{name}={ver}")
print("PACKAGES=" + shlex.quote(" ".join(pkgs)))
print("HOLD=" + shlex.quote(" ".join(apt["packages"])))
PY
)"
  SNAPSHOT_LIST=/etc/apt/sources.list.d/social-nav-ros-snapshot.list
  printf 'deb [arch=amd64 signed-by=%s] %s %s main\n' \
    "$KEYRING" "$SNAPSHOT" "$SNAPSHOT_DIST" > "$SNAPSHOT_LIST"
  apt-get update
  # Install lock versions even if another version is already present.
  # shellcheck disable=SC2086
  apt-get install -y --allow-downgrades $PACKAGES
  # shellcheck disable=SC2086
  apt-mark hold $HOLD
  extra="$(dpkg-query -W -f='${Package}\n' 'ros-jazzy-nav2-*' 'ros-jazzy-navigation2' 2>/dev/null || true)"
  if [[ -n "$extra" ]]; then
    # shellcheck disable=SC2086
    apt-mark hold $extra
  fi
  exit 0
fi

exec "$ROOT/scripts/doctor.sh"
