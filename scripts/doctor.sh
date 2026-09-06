#!/usr/bin/env bash
# Check OS, ROS, sibling handover SHAs, and the assets bundle checksum when present.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
LOCK="$ROOT/components.lock.yaml"
fail=0

say() { printf '%s\n' "$*"; }
bad() { printf 'FAIL %s\n' "$*" >&2; fail=1; }

os="$(. /etc/os-release && echo "${ID}-${VERSION_ID}-${VERSION_CODENAME}")"
say "os: $os"
if [[ "$os" != ubuntu-24.04-noble ]]; then
  say "NOTE: supported runtime is Ubuntu 24.04 x86_64 (found $os)"
fi

say "python: $(python3 --version 2>/dev/null || echo missing)"
say "ros: ${ROS_DISTRO:-unset}"

python3 - "$ROOT" "$LOCK" <<'PY' || fail=1
import hashlib, sys
from pathlib import Path
import yaml

root = Path(sys.argv[1])
lock = yaml.safe_load(Path(sys.argv[2]).read_text())
ok = True
for name, spec in lock.items():
    if name == "scientific_freeze":
        continue
    rel = spec["path"]
    path = (root / rel).resolve()
    sha = spec["sha"]
    git = path / ".git"
    if not git.exists():
        print(f"FAIL {name}: missing {path}", file=sys.stderr)
        ok = False
        continue
    import subprocess
    got = subprocess.check_output(["git", "-C", str(path), "rev-parse", "HEAD"], text=True).strip()
    if got != sha:
        print(f"FAIL {name}: HEAD {got} != {sha}", file=sys.stderr)
        ok = False
    else:
        print(f"OK   {name}: {got[:7]}")
    if name == "assets":
        bundle = path / spec["bundle"]
        if bundle.is_file():
            h = hashlib.sha256(bundle.read_bytes()).hexdigest()
            if h != spec["bundle_sha256"]:
                print(f"FAIL assets bundle sha256 {h}", file=sys.stderr)
                ok = False
            else:
                print("OK   assets bundle")
        else:
            print("NOTE assets bundle not unpacked locally (gitignored dist/)")
sys.exit(0 if ok else 1)
PY

isaac="${SOCIAL_NAV_ISAAC_PATH:-$HOME/isaacsim/python.sh}"
if [[ -x "$isaac" ]]; then
  say "isaac: $isaac"
else
  say "NOTE: Isaac python not found at $isaac (set SOCIAL_NAV_ISAAC_PATH)"
fi

if [[ "$fail" -ne 0 ]]; then
  exit 1
fi
say "doctor OK"
exit 0
