#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
rm -rf "$ROOT/build" "$ROOT/install" "$ROOT/log" "$ROOT/cache"
