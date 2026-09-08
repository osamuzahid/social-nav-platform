#!/usr/bin/env bash
# Check OS, ROS, sibling SHAs, USD bundle, and unpacked campaign assets.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
LOCK="$ROOT/components.lock.yaml"
fail=0

say() { printf '%s\n' "$*"; }

os="$(. /etc/os-release && echo "${ID}-${VERSION_ID}-${VERSION_CODENAME}")"
say "os: $os"
if [[ "$os" != ubuntu-24.04-noble ]]; then
  say "NOTE: supported runtime is Ubuntu 24.04 x86_64 (found $os)"
fi

say "python: $(python3 --version 2>/dev/null || echo missing)"
say "ros: ${ROS_DISTRO:-unset}"

python3 - "$ROOT" "$LOCK" <<'PY' || fail=1
import hashlib, subprocess, sys
from pathlib import Path
import yaml

root = Path(sys.argv[1])
sys.path.insert(0, str(root / "src"))
from social_nav_runner.layout import Layout

lock = yaml.safe_load(Path(sys.argv[2]).read_text())
ok = True
assets_path = None
bundle_spec = None
for name, spec in lock.items():
    if name == "scientific_freeze":
        continue
    path = (root / spec["path"]).resolve()
    sha = spec["sha"]
    if not (path / ".git").exists():
        print(f"FAIL {name}: missing {path}", file=sys.stderr)
        ok = False
        continue
    got = subprocess.check_output(
        ["git", "-C", str(path), "rev-parse", "HEAD"], text=True
    ).strip()
    if got != sha:
        print(f"FAIL {name}: HEAD {got} != {sha}", file=sys.stderr)
        ok = False
    else:
        print(f"OK   {name}: {got[:7]}")
    if name == "assets":
        assets_path = path
        bundle_spec = spec

layout = Layout.discover(root)
missing = layout.missing_runtime_assets()

if bundle_spec is not None and assets_path is not None:
    bundle = assets_path / bundle_spec["bundle"]
    if bundle.is_file():
        digest = hashlib.sha256(bundle.read_bytes()).hexdigest()
        if digest != bundle_spec["bundle_sha256"]:
            print(f"FAIL assets bundle sha256 {digest}", file=sys.stderr)
            ok = False
        else:
            print("OK   assets bundle")
    elif missing:
        print(
            f"FAIL assets bundle missing {bundle} (run scripts/unpack-assets.sh)",
            file=sys.stderr,
        )
        ok = False
    else:
        print("NOTE assets bundle not present (campaign USDs already unpacked)")

if missing:
    print("FAIL unpacked USDs missing (run scripts/unpack-assets.sh):", file=sys.stderr)
    for item in missing:
        print(f"     {item}", file=sys.stderr)
    ok = False
else:
    print("OK   campaign USDs")

sys.exit(0 if ok else 1)
PY

isaac="${SOCIAL_NAV_ISAAC_PATH:-$HOME/isaacsim/python.sh}"
if [[ -x "$isaac" ]]; then
  say "isaac: $isaac"
else
  say "NOTE: Isaac python not found at $isaac (set SOCIAL_NAV_ISAAC_PATH)"
fi

HUNAV_SETUP="$(python3 - "$ROOT" "$LOCK" <<'PY'
from pathlib import Path
import sys, yaml
root = Path(sys.argv[1])
lock = yaml.safe_load(Path(sys.argv[2]).read_text())
print((root / lock["hunav"]["path"]).resolve() / "install" / "setup.bash")
PY
)"
ESC_SETUP="$(python3 - "$ROOT" "$LOCK" <<'PY'
from pathlib import Path
import sys, yaml
root = Path(sys.argv[1])
lock = yaml.safe_load(Path(sys.argv[2]).read_text())
print((root / lock["esc"]["path"]).resolve() / "install" / "setup.bash")
PY
)"

if [[ -n "${SOCIAL_NAV_ROS_SETUP:-}" ]]; then
  say "ros_overlay: $SOCIAL_NAV_ROS_SETUP"
elif [[ -f "$HUNAV_SETUP" ]]; then
  say "hunav_overlay: $HUNAV_SETUP"
else
  say "NOTE: run ./scripts/build.sh (or set SOCIAL_NAV_ROS_SETUP) so hunav_agent_manager is on the overlay"
fi

if [[ -n "${SOCIAL_NAV_ESC_SETUP:-}" ]]; then
  say "esc_overlay: $SOCIAL_NAV_ESC_SETUP"
elif [[ -f "$ESC_SETUP" ]]; then
  say "esc_overlay: $ESC_SETUP"
else
  say "NOTE: run ./scripts/build.sh (or set SOCIAL_NAV_ESC_SETUP) for ESC hops"
fi

if [[ "$fail" -ne 0 ]]; then
  exit 1
fi
say "doctor OK"
exit 0
