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
  eval "$(python3 - "$LOCK" "$ROOT" <<'PY'
import shlex, subprocess, sys
from pathlib import Path
import yaml

lock_path = Path(sys.argv[1])
root = Path(sys.argv[2])
lock = yaml.safe_load(lock_path.read_text(encoding="utf-8"))
apt = lock["apt"]
key_file = (root / apt["ros_snapshot_key"]).resolve()
if not key_file.is_file():
    print(f"dependency_error: missing snapshot key {key_file}", file=sys.stderr)
    sys.exit(1)
out = subprocess.check_output(
    ["gpg", "--show-keys", "--with-colons", str(key_file)],
    env={k: v for k, v in __import__("os").environ.items() if k != "GNUPGHOME"},
    text=True,
)
fprs = [line.split(":")[9] for line in out.splitlines() if line.startswith("fpr:")]
want = apt["ros_snapshot_key_fingerprint"].replace(" ", "").upper()
if not fprs or fprs[0].upper() != want:
    got = fprs[0] if fprs else "missing"
    print(
        f"dependency_error: snapshot key fingerprint {got} != {want}",
        file=sys.stderr,
    )
    sys.exit(1)
print("SNAPSHOT=" + shlex.quote(apt["ros_snapshot"]))
print("SNAPSHOT_DIST=" + shlex.quote(apt["ros_snapshot_dist"]))
print("KEY_FILE=" + shlex.quote(str(key_file)))
print("KEYRING=" + shlex.quote(apt["ros_snapshot_keyring"]))
pkgs = []
for name, ver in apt["packages"].items():
    pkgs.append(f"{name}={ver}")
print("PACKAGES=" + shlex.quote(" ".join(pkgs)))
print("HOLD=" + shlex.quote(" ".join(apt["packages"])))
PY
)"
  install -d -m 0755 "$(dirname "$KEYRING")"
  unset GNUPGHOME
  gpg --batch --yes --dearmor -o "$KEYRING" "$KEY_FILE"
  chmod 0644 "$KEYRING"
  SNAPSHOT_LIST=/etc/apt/sources.list.d/social-nav-ros-snapshot.list
  printf 'deb [arch=amd64 signed-by=%s] %s %s main\n' \
    "$KEYRING" "$SNAPSHOT" "$SNAPSHOT_DIST" > "$SNAPSHOT_LIST"
  if ! apt-get update; then
    rm -f "$SNAPSHOT_LIST"
    echo "dependency_error: apt-get update failed for $SNAPSHOT (removed $SNAPSHOT_LIST)" >&2
    exit 1
  fi
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
