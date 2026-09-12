#!/usr/bin/env bash
set -euo pipefail
export PYTHONDONTWRITEBYTECODE=1
cd "$(dirname "$0")/.."
node scripts/check.mjs
node scripts/test-receivables.mjs
python3 -B scripts/test-free-release.py
python3 -B scripts/build_packages.py
