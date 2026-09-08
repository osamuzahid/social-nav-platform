#!/usr/bin/env bash
# Extract the checksummed USD bundle into the sibling assets tree.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
LOCK="$ROOT/components.lock.yaml"

python3 - "$ROOT" "$LOCK" <<'PY'
import hashlib, subprocess, sys
from pathlib import Path
import yaml

root = Path(sys.argv[1])
lock = yaml.safe_load(Path(sys.argv[2]).read_text(encoding="utf-8"))
spec = lock["assets"]
assets = (root / spec["path"]).resolve()
bundle = assets / spec["bundle"]
if not bundle.is_file():
    print(
        f"asset_error: missing {bundle}\n"
        "Place the prebuilt USD tarball at that path, then rerun.",
        file=sys.stderr,
    )
    sys.exit(1)
digest = hashlib.sha256(bundle.read_bytes()).hexdigest()
want = spec["bundle_sha256"]
if digest != want:
    print(f"asset_error: bundle sha256 {digest} != {want}", file=sys.stderr)
    sys.exit(1)
subprocess.run(
    ["tar", "--zstd", "-xf", str(bundle), "-C", str(assets)],
    check=True,
)
print(f"unpacked {bundle.name} into {assets}")
PY
