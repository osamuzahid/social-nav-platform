#!/usr/bin/env bash
# Check OS, ROS, sibling SHAs, USD bundle, unpacked campaign assets, and
# lock apt versions. Host tooling (Isaac, driver, lightsfm, …) is noted.
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

ISAAC="${SOCIAL_NAV_ISAAC_PATH:-$HOME/isaacsim/python.sh}"
export SOCIAL_NAV_ISAAC_PATH="$ISAAC"

python3 - "$ROOT" "$LOCK" <<'PY' || fail=1
import hashlib, os, subprocess, sys
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
    if not isinstance(spec, dict) or "path" not in spec or "sha" not in spec:
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


def dpkg_version(name: str) -> str | None:
    proc = subprocess.run(
        ["dpkg-query", "-W", "-f=${Version}", name],
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        return None
    return proc.stdout.strip() or None


def parse_ver(text: str) -> tuple[int, ...]:
    parts = []
    for bit in text.split("."):
        digits = "".join(c for c in bit if c.isdigit())
        parts.append(int(digits) if digits else 0)
    return tuple(parts)


def ver_lt(got: str, minimum: str) -> bool:
    a, b = parse_ver(got), parse_ver(minimum)
    n = max(len(a), len(b))
    a = a + (0,) * (n - len(a))
    b = b + (0,) * (n - len(b))
    return a < b


def lightsfm_sha256(include: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(include.rglob("*")):
        if path.is_file():
            digest.update(path.relative_to(include).as_posix().encode())
            digest.update(path.read_bytes())
    return digest.hexdigest()


apt = lock.get("apt") or {}
for name, want in (apt.get("packages") or {}).items():
    got = dpkg_version(name)
    if got is None:
        print(f"NOTE {name}: not installed (run sudo ./scripts/bootstrap.sh --install-system-deps)")
    elif got != want:
        print(f"FAIL {name}: {got} != {want}", file=sys.stderr)
        ok = False
    else:
        print(f"OK   {name}: {got}")

env = lock.get("environment") or {}
isaac = Path(os.environ.get("SOCIAL_NAV_ISAAC_PATH", Path.home() / "isaacsim" / "python.sh"))
want_isaac = env.get("isaac_version")
if not isaac.is_file():
    print(f"NOTE isaac python not found at {isaac} (set SOCIAL_NAV_ISAAC_PATH)")
elif want_isaac:
    version_path = isaac.resolve().parent / "VERSION"
    if not version_path.is_file():
        print(f"NOTE isaac VERSION missing next to {isaac}")
    else:
        got_isaac = version_path.read_text(encoding="utf-8").strip()
        if got_isaac != want_isaac:
            print(f"NOTE isaac {got_isaac} (tested {want_isaac})")
        else:
            print(f"OK   isaac: {got_isaac}")

want_py = env.get("python")
if want_py:
    got_py = sys.version.split()[0]
    if got_py != want_py:
        print(f"NOTE python {got_py} (tested {want_py})")
    else:
        print(f"OK   python: {got_py}")

for mod, key in (("pandas", "pandas"), ("numpy", "numpy")):
    want = env.get(key)
    if not want:
        continue
    try:
        got_mod = __import__(mod).__version__
    except Exception:
        print(f"NOTE {mod}: not importable (tested {want})")
        continue
    if got_mod != want:
        print(f"NOTE {mod} {got_mod} (tested {want})")
    else:
        print(f"OK   {mod}: {got_mod}")

want_assimp = env.get("assimp_utils")
if want_assimp:
    got_assimp = dpkg_version("assimp-utils")
    if got_assimp is None:
        print(f"NOTE assimp-utils: not installed (tested {want_assimp})")
    elif got_assimp != want_assimp:
        print(f"NOTE assimp-utils {got_assimp} (tested {want_assimp})")
    else:
        print(f"OK   assimp-utils: {got_assimp}")

want_drv = env.get("nvidia_driver")
min_drv = env.get("nvidia_driver_minimum")
proc = subprocess.run(
    ["nvidia-smi", "--query-gpu=driver_version", "--format=csv,noheader"],
    capture_output=True,
    text=True,
)
got_drv = proc.stdout.strip().splitlines()[0].strip() if proc.returncode == 0 and proc.stdout.strip() else None
if got_drv is None:
    print("NOTE nvidia driver: nvidia-smi not available")
elif min_drv and ver_lt(got_drv, min_drv):
    print(f"NOTE nvidia driver {got_drv} (minimum {min_drv})")
elif want_drv and got_drv != want_drv:
    print(f"NOTE nvidia driver {got_drv} (tested {want_drv})")
elif want_drv:
    print(f"OK   nvidia driver: {got_drv}")

include = Path(env.get("lightsfm_include") or "/usr/local/include/lightsfm")
want_sfm = env.get("lightsfm_include_sha256")
if want_sfm:
    if not include.is_dir():
        print(f"NOTE lightsfm headers missing at {include}")
    else:
        got_sfm = lightsfm_sha256(include)
        if got_sfm != want_sfm:
            print(f"NOTE lightsfm include sha256 {got_sfm} (tested {want_sfm})")
        else:
            print(f"OK   lightsfm include: {include}")

sys.exit(0 if ok else 1)
PY

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
